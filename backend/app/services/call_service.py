import logging
import time
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.call import CallSession

logger = logging.getLogger(__name__)

# Twilio Network Traversal Service (their TURN/STUN product) reuses the exact
# same TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN already configured for Twilio
# Verify (SMS) and Lookup elsewhere in this app — it's a different product on
# the same account, not a separate credential to go provision. See
# https://www.twilio.com/docs/stun-turn/api. A minted token is valid for its
# own `ttl` (usually 86400s); cached in-process and refreshed a bit early so
# an outgoing call practically never waits on this HTTP round trip.
_cached_twilio_ice_servers: list[dict] | None = None
_cache_expires_at_monotonic: float = 0.0


async def get_twilio_ice_servers() -> list[dict] | None:
    """Returns Twilio's STUN+TURN ice_servers list, or None if Twilio isn't
    configured (no account_sid/auth_token) or the request fails — callers
    fall back to the static STUN_URLS/TURN_URL config in that case, same
    "degrade, don't 503" convention as every other optional integration in
    this app."""
    global _cached_twilio_ice_servers, _cache_expires_at_monotonic
    if _cached_twilio_ice_servers is not None and time.monotonic() < _cache_expires_at_monotonic:
        return _cached_twilio_ice_servers
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        return None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Tokens.json",
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # noqa: BLE001 - network hiccup or bad credentials: never fatal, just fall back to STUN-only
        logger.exception("failed to fetch Twilio TURN credentials")
        return None

    ice_servers = [
        {"urls": s["urls"], **({"username": s["username"], "credential": s["credential"]} if "username" in s else {})}
        for s in data.get("ice_servers", [])
        if "urls" in s
    ]
    if not ice_servers:
        return None

    _cached_twilio_ice_servers = ice_servers
    ttl_seconds = int(data.get("ttl") or 3600)
    _cache_expires_at_monotonic = time.monotonic() + max(ttl_seconds - 300, 60)
    return ice_servers


async def create_call(
    db: AsyncSession, match_id: uuid.UUID, caller_id: uuid.UUID, callee_id: uuid.UUID, call_type: str = "video"
) -> CallSession:
    call = CallSession(
        match_id=match_id,
        caller_id=caller_id,
        callee_id=callee_id,
        status="ringing",
        call_type=call_type if call_type in ("video", "audio") else "video",
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call


async def get_active_call_for_user(db: AsyncSession, call_id: uuid.UUID, user_id: uuid.UUID) -> CallSession | None:
    call = await db.get(CallSession, call_id)
    if call is None or user_id not in (call.caller_id, call.callee_id):
        return None
    if call.status not in ("ringing", "active"):
        return None
    return call


async def get_ringing_or_active_call_for_match(db: AsyncSession, match_id: uuid.UUID) -> CallSession | None:
    return await db.scalar(
        select(CallSession)
        .where(CallSession.match_id == match_id, CallSession.status.in_(("ringing", "active")))
        .order_by(CallSession.started_at.desc())
    )


def other_participant(call: CallSession, user_id: uuid.UUID) -> uuid.UUID:
    return call.callee_id if call.caller_id == user_id else call.caller_id


async def mark_answered(db: AsyncSession, call: CallSession) -> None:
    call.status = "active"
    call.connected_at = datetime.now(timezone.utc)
    await db.commit()


async def mark_ended(db: AsyncSession, call: CallSession, reason: str) -> None:
    call.status = "declined" if reason == "declined" else "ended"
    call.end_reason = reason
    call.ended_at = datetime.now(timezone.utc)
    await db.commit()


async def end_active_calls_for_user(db: AsyncSession, user_id: uuid.UUID, reason: str = "peer_offline") -> list[CallSession]:
    """Called on WS disconnect — ends any in-progress call this user was
    part of and returns them so the caller can notify the peer."""
    calls = (
        await db.execute(
            select(CallSession).where(
                CallSession.status.in_(("ringing", "active")),
                or_(CallSession.caller_id == user_id, CallSession.callee_id == user_id),
            )
        )
    ).scalars().all()
    for call in calls:
        call.status = "ended"
        call.end_reason = reason
        call.ended_at = datetime.now(timezone.utc)
    if calls:
        await db.commit()
    return list(calls)
