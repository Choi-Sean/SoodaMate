import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Match
from app.models.message import Message

REPLY_WINDOW = timedelta(hours=24)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _is_expired(match: Match) -> bool:
    now = datetime.now(timezone.utc)
    if not match.first_message_sent:
        # Nobody has said anything yet — Phase 14's gender-restricted
        # first-message deadline (unrestricted pairs have no deadline and
        # never expire pre-first-message).
        if match.first_message_deadline is None:
            return False
        return now >= _aware(match.first_message_deadline)
    # Someone has spoken — the conversation goes stale if nobody has
    # replied to the most recent message within 24h. last_activity_at is
    # None only for rows written before this column existed; matched_at is
    # the correct fallback since first_message_sent is already True there.
    last_activity = match.last_activity_at or match.matched_at
    return now >= _aware(last_activity) + REPLY_WINDOW


async def _get_match_for_participant(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID
) -> Match | None:
    match = await db.get(Match, match_id)
    if match is None:
        return None
    if user_id not in (match.user_a_id, match.user_b_id):
        return None
    # Lazy expiry: the single choke point every real touchpoint (WS
    # handler, REST history route, list_matches) goes through, so a match
    # past its deadline/reply window flips inactive here rather than
    # needing a scheduler this app doesn't have.
    if match.is_active and _is_expired(match):
        match.is_active = False
        await db.commit()
    return match


async def get_active_match_for_user(
    db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID
) -> Match | None:
    """Requires the match still be active — gates *sending* a message
    (and the WS read-receipt/call-signaling paths)."""
    match = await _get_match_for_participant(db, match_id, user_id)
    return match if match and match.is_active else None


async def get_match_for_user(db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID) -> Match | None:
    """Participant check only, active or not — a conversation's past
    messages stay readable after it goes stale; only sending into it is
    blocked (see get_active_match_for_user)."""
    return await _get_match_for_participant(db, match_id, user_id)


def is_message_allowed(match: Match, sender_id: uuid.UUID) -> bool:
    """Phase 14: True unless this match is still restricted-and-unmet and
    the sender isn't the one allowed to send first."""
    if match.restricted_to_user_id is None or match.first_message_sent:
        return True
    return sender_id == match.restricted_to_user_id


def other_participant(match: Match, user_id: uuid.UUID) -> uuid.UUID:
    return match.user_b_id if match.user_a_id == user_id else match.user_a_id


async def persist_message(
    db: AsyncSession,
    match: Match,
    sender_id: uuid.UUID,
    content: str,
    message_type: str = "text",
    image_object_path: str | None = None,
    original_language: str | None = None,
    translated_content: str | None = None,
    translated_language: str | None = None,
) -> Message:
    message = Message(
        match_id=match.id,
        sender_id=sender_id,
        content=content,
        message_type=message_type,
        image_object_path=image_object_path,
        original_language=original_language,
        translated_content=translated_content,
        translated_language=translated_language,
    )
    db.add(message)
    if not match.first_message_sent:
        match.first_message_sent = True
    match.last_activity_at = datetime.now(timezone.utc)
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
