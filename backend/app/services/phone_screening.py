import logging
import re
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)

TWILIO_LOOKUP_API_BASE = "https://lookups.twilio.com/v2"

# The mobile app matches this exact string to show a localized message (see
# PhoneAuthScreen / PhoneVerificationScreen) — change both sides together.
VIRTUAL_NUMBER_DETAIL = "virtual phone numbers are not allowed"

# Korea: a real mobile number is 010 (plus grandfathered 011/016-019), i.e.
# +82 10... / +82 11... Everything else — 070 internet phone, 050x "safe"
# numbers, 02/031... landlines — is not a phone a person carries around.
# Free and exact, so it runs even when the paid Lookup below is off.
KR_MOBILE_PATTERN = re.compile(r"^\+821[016789]\d{7,8}$")

# Twilio Lookup v2 Line Type Intelligence values we refuse. Only `mobile` is
# accepted; `unknown` (or any lookup failure) is deliberately let through —
# see _lookup_line_type — so a Twilio hiccup or an unclassifiable real
# number doesn't lock people out of signup.
BLOCKED_LINE_TYPES = frozenset(
    {
        "fixedVoip",
        "nonFixedVoip",  # Google Voice, TextNow, etc.
        "landline",  # can't receive the SMS code anyway
        "tollFree",
        "premium",
        "sharedCost",
        "uan",
        "voicemail",
        "pager",
        "personal",
    }
)


async def _lookup_line_type(phone_number: str) -> str | None:
    """Twilio Lookup v2 line type, or None if it couldn't be determined.
    Costs ~$0.008/request (twilio.com/lookup/pricing), so callers gate on
    settings.block_voip_phone_numbers and only call it for numbers that
    aren't already known accounts."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{TWILIO_LOOKUP_API_BASE}/PhoneNumbers/{quote(phone_number, safe='')}",
                params={"Fields": "line_type_intelligence"},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
    except httpx.HTTPError as exc:
        logger.warning("twilio lookup unreachable, letting number through: %s", exc)
        return None

    if resp.status_code >= 400:
        # Includes 401/403 (bad credentials, account without Line Type
        # Intelligence access) — logged loudly since it silently disables the
        # filter until fixed.
        logger.error("twilio lookup failed (%s), letting number through: %s", resp.status_code, resp.text[:300])
        return None

    intel = resp.json().get("line_type_intelligence") or {}
    if intel.get("error_code"):
        logger.warning("twilio line type error_code=%s, letting number through", intel["error_code"])
        return None
    return intel.get("type")


async def assert_real_mobile_number(phone_number: str) -> None:
    """Rejects internet (VoIP) / virtual / landline numbers with 400
    VIRTUAL_NUMBER_DETAIL. `phone_number` must already be normalized E.164."""
    if phone_number.startswith("+82") and not KR_MOBILE_PATTERN.match(phone_number):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, VIRTUAL_NUMBER_DETAIL)

    if not settings.block_voip_phone_numbers:
        return
    if not (settings.twilio_account_sid and settings.twilio_auth_token):
        return

    if await _lookup_line_type(phone_number) in BLOCKED_LINE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, VIRTUAL_NUMBER_DETAIL)
