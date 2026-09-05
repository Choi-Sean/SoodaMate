import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import CallSession


async def create_call(db: AsyncSession, match_id: uuid.UUID, caller_id: uuid.UUID, callee_id: uuid.UUID) -> CallSession:
    call = CallSession(match_id=match_id, caller_id=caller_id, callee_id=callee_id, status="ringing")
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
