import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Match
from app.models.message import Message


def _is_expired(match: Match) -> bool:
    if match.first_message_sent or match.first_message_deadline is None:
        return False
    deadline = match.first_message_deadline
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= deadline


async def get_active_match_for_user(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID
) -> Match | None:
    match = await db.get(Match, match_id)
    if match is None:
        return None
    if user_id not in (match.user_a_id, match.user_b_id):
        return None
    # Phase 14 lazy expiry: the single choke point both the WS handler and
    # the REST history route go through, so a match with an unmet 24h
    # first-message deadline flips inactive here rather than needing a
    # scheduler this app doesn't have.
    if match.is_active and _is_expired(match):
        match.is_active = False
        await db.commit()
    return match if match.is_active else None


def is_message_allowed(match: Match, sender_id: uuid.UUID) -> bool:
    """Phase 14: True unless this match is still restricted-and-unmet and
    the sender isn't the one allowed to send first."""
    if match.restricted_to_user_id is None or match.first_message_sent:
        return True
    return sender_id == match.restricted_to_user_id


def other_participant(match: Match, user_id: uuid.UUID) -> uuid.UUID:
    return match.user_b_id if match.user_a_id == user_id else match.user_a_id


async def persist_message(db: AsyncSession, match: Match, sender_id: uuid.UUID, content: str) -> Message:
    message = Message(match_id=match.id, sender_id=sender_id, content=content)
    db.add(message)
    if not match.first_message_sent:
        match.first_message_sent = True
    await db.commit()
    await db.refresh(message)
    return message


async def mark_read(db: AsyncSession, match_id: uuid.UUID, reader_id: uuid.UUID) -> None:
    await db.execute(
        Message.__table__.update()
        .where(
            Message.match_id == match_id,
            Message.sender_id != reader_id,
            Message.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()


async def get_history(
    db: AsyncSession, match_id: uuid.UUID, before: datetime | None, limit: int
) -> list[Message]:
    stmt = select(Message).where(Message.match_id == match_id)
    if before is not None:
        stmt = stmt.where(Message.sent_at < before)
    stmt = stmt.order_by(Message.sent_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return list(reversed(rows))
