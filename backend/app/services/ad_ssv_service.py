"""Server-side verification (SSV) of AdMob rewarded ads.

Without this the "watch an ad, get a bonus match" reward is honour-system: the
client says "I watched it" (POST /blind-chat/ad-bonus) and anyone can say that
from a script without ever loading an ad. With SSV, Google's servers call
GET /ads/ssv after a rewarded ad really completes, signing the callback with
ECDSA; only that signed callback grants the bonus.

https://developers.google.com/admob/android/ssv
"""
import base64
import logging
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.profile import Profile

logger = logging.getLogger(__name__)

KEYS_URL = "https://www.gstatic.com/admob/reward/verifier-keys.json"
KEY_CACHE_SECONDS = 24 * 3600
# A callback older than this is refused — the signed URL could otherwise be
# replayed on a later day to re-grant that day's bonus.
MAX_CALLBACK_AGE_SECONDS = 15 * 60

_cache: dict = {"keys": None, "fetched_at": 0.0}
_test_keys: dict[str, str] | None = None


def set_test_keys(keys: dict[str, str] | None) -> None:
    """Tests inject their own {key_id: PEM} instead of fetching Google's."""
    global _test_keys
    _test_keys = keys


async def _fetch_google_keys() -> dict[str, str]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(KEYS_URL)
        resp.raise_for_status()
    return {str(k["keyId"]): k["pem"] for k in resp.json().get("keys", [])}


async def _get_key(key_id: str, *, refresh: bool = False) -> str | None:
    if _test_keys is not None:
        return _test_keys.get(key_id)
    now = time.time()
    if refresh or _cache["keys"] is None or now - _cache["fetched_at"] > KEY_CACHE_SECONDS:
        try:
            _cache["keys"] = await _fetch_google_keys()
            _cache["fetched_at"] = now
        except Exception:  # noqa: BLE001 - keep serving from a stale cache if Google is unreachable
            logger.warning("could not refresh AdMob SSV verifier keys", exc_info=True)
            if _cache["keys"] is None:
                return None
    return _cache["keys"].get(key_id)


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


async def verify_and_grant(db: AsyncSession, raw_query: str) -> None:
    """Verifies Google's signature over the callback's query string and, if the
    ad really was ours and recent, grants today's rewarded-ad bonus to
    `user_id`. Raises HTTPException(400/403) for anything that doesn't check out."""
    marker = "&signature="
    idx = raw_query.find(marker)
    if idx == -1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing signature")
    signed_message = raw_query[:idx]
    params = {k: v[0] for k, v in parse_qs(raw_query, keep_blank_values=True).items()}
    signature, key_id = params.get("signature"), params.get("key_id")
    if not signature or not key_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "missing signature or key_id")

    pem = await _get_key(key_id) or await _get_key(key_id, refresh=True)
    if pem is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "unknown verifier key")
    try:
        public_key = serialization.load_pem_public_key(pem.encode())
        public_key.verify(_b64url_decode(signature), signed_message.encode(), ec.ECDSA(hashes.SHA256()))
    except (InvalidSignature, ValueError, TypeError):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid signature") from None

    # Anyone with an AdMob account can have Google sign a callback for THEIR ad
    # unit with an arbitrary user_id, so only our own rewarded units count.
    allowed_units = settings.admob_rewarded_unit_id_list
    if not allowed_units or params.get("ad_unit") not in allowed_units:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ad unit not accepted")

    try:
        issued_ms = int(params.get("timestamp", ""))
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad timestamp") from None
    if abs(time.time() - issued_ms / 1000) > MAX_CALLBACK_AGE_SECONDS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "callback too old")

    try:
        user_id = uuid.UUID(params.get("user_id", ""))
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad user_id") from None
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown user")

    today = datetime.now(timezone.utc).date()
    if profile.blind_chat_bonus_ad_watched_on != today:
        profile.blind_chat_bonus_ad_watched_on = today
        await db.commit()
