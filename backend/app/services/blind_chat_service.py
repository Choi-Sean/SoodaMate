import uuid
from datetime import date, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Block, Match
from app.models.blind_chat import BlindChatQueueEntry
from app.models.profile import Profile
from app.models.user import User
from app.schemas.match import BlindChatQueueStatusOut
from app.services import push_service
from app.ws.connection_manager import manager


def _csv_contains_any(column, values: list[str]):
    """Same portable comma-list "contains any of" match as
    discovery_service._csv_contains_any — duplicated locally (three lines)
    rather than importing a module-private helper across services."""
    wrapped = func.concat(",", column, ",")
    return or_(*[wrapped.like(f"%,{v},%") for v in values])


def _age_to_birth_date_bounds(min_age: int, max_age: int) -> tuple[date, date]:
    today = date.today()
    max_birth_date = today.replace(year=today.year - min_age)
    min_birth_date = today.replace(year=today.year - max_age - 1) + timedelta(days=1)
    return min_birth_date, max_birth_date


def _age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _blind_reveal_eligible_user_id(profile_a: Profile, profile_b: Profile) -> uuid.UUID | None:
    """Same snapshot-at-creation-time convention as Match.restricted_to_user_id:
    a male/female pair restricts reveal-requests to the female side; anything
    else (same-gender, or either profile is "other") leaves it NULL — either
    side may propose. See the soodamate-blind-chat-open-decisions memory
    note: that "either side" default for the non-mixed case is a deliberate
    placeholder, not a final decision."""
    if profile_a.gender == "female" and profile_b.gender == "male":
        return profile_a.user_id
    if profile_b.gender == "female" and profile_a.gender == "male":
        return profile_b.user_id
    return None


async def _find_waiting_partner(
    db: AsyncSession, user: User, viewer_profile: Profile, categories: list[str]
) -> tuple[BlindChatQueueEntry, Profile] | None:
    viewer_min_birth, viewer_max_birth = _age_to_birth_date_bounds(
        viewer_profile.min_age_pref, viewer_profile.max_age_pref
    )
    viewer_age = _age(viewer_profile.birth_date)

    gender_filters = [Profile.gender == viewer_profile.interested_in] if viewer_profile.interested_in != "all" else []
    mutual_interest = or_(Profile.interested_in == "all", Profile.interested_in == viewer_profile.gender)

    blocked_either_direction = select(Block.id).where(
        or_(
            and_(Block.blocker_id == user.id, Block.blocked_id == BlindChatQueueEntry.user_id),
            and_(Block.blocker_id == BlindChatQueueEntry.user_id, Block.blocked_id == user.id),
        )
    ).exists()

    stmt = (
        select(BlindChatQueueEntry, Profile)
        .join(Profile, Profile.user_id == BlindChatQueueEntry.user_id)
        .join(User, User.id == BlindChatQueueEntry.user_id)
        .where(
            BlindChatQueueEntry.user_id != user.id,
            BlindChatQueueEntry.matched_id.is_(None),
            ~User.is_banned,
            User.is_active,
            _csv_contains_any(BlindChatQueueEntry.categories, categories),
            mutual_interest,
            *gender_filters,
            # Mutual age preference — candidate must be within the viewer's
            # requested range AND the viewer must be within the candidate's.
            Profile.birth_date >= viewer_min_birth,
            Profile.birth_date <= viewer_max_birth,
            Profile.min_age_pref <= viewer_age,
            Profile.max_age_pref >= viewer_age,
            ~blocked_either_direction,
        )
        .order_by(BlindChatQueueEntry.created_at.asc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    return (row[0], row[1]) if row else None


async def join_queue(
    db: AsyncSession, user: User, viewer_profile: Profile, categories: list[str]
) -> BlindChatQueueStatusOut:
    existing = await db.scalar(select(BlindChatQueueEntry).where(BlindChatQueueEntry.user_id == user.id))
    if existing is not None:
        # Already waiting: either still waiting (idempotent no-op — cancel
        # first to change categories), or someone else's queue call already
        # claimed this entry for a match since the caller last checked.
        return await _resolve_own_entry(db, existing)

    found = await _find_waiting_partner(db, user, viewer_profile, categories)
    if found is None:
        db.add(BlindChatQueueEntry(user_id=user.id, categories=",".join(categories)))
        await db.commit()
        return BlindChatQueueStatusOut(status="waiting")

    partner_entry, partner_profile = found
    shared = sorted(set(categories) & set(partner_entry.categories.split(",")))

    ordered = sorted([(user.id, viewer_profile), (partner_entry.user_id, partner_profile)], key=lambda t: str(t[0]))
    (a_id, prof_a), (b_id, prof_b) = ordered

    match = Match(
        user_a_id=a_id,
        user_b_id=b_id,
        is_blind=True,
        blind_categories=",".join(shared),
        blind_reveal_eligible_user_id=_blind_reveal_eligible_user_id(prof_a, prof_b),
        restricted_to_user_id=None,
        first_message_deadline=None,
    )
    db.add(match)
    await db.flush()  # need match.id before it can be stamped onto the entry
    # Marked as claimed, not deleted — the waiting side's own next
    # GET/POST /blind-chat/queue discovers the match this way (see
    # _resolve_own_entry / BlindChatQueueEntry.matched_id's docstring for
    # why this is relational rather than a time-window check).
    partner_entry.matched_id = match.id
    await db.commit()
    await db.refresh(match)

    delivered = await manager.send_to_user(
        partner_entry.user_id, {"type": "blind_chat_matched", "match_id": str(match.id)}
    )
    if not delivered:
        await push_service.send_blind_chat_matched_notification(db, partner_entry.user_id, match.id)

    return BlindChatQueueStatusOut(status="matched", match_id=match.id)


async def _resolve_own_entry(db: AsyncSession, entry: BlindChatQueueEntry) -> BlindChatQueueStatusOut:
    if entry.matched_id is None:
        return BlindChatQueueStatusOut(status="waiting")
    match_id = entry.matched_id
    await db.delete(entry)
    await db.commit()
    return BlindChatQueueStatusOut(status="matched", match_id=match_id)


async def cancel_queue(db: AsyncSession, user_id: uuid.UUID) -> bool:
    entry = await db.scalar(select(BlindChatQueueEntry).where(BlindChatQueueEntry.user_id == user_id))
    if entry is None:
        return False
    await db.delete(entry)
    await db.commit()
    return True


async def get_queue_status(db: AsyncSession, user_id: uuid.UUID) -> BlindChatQueueStatusOut:
    entry = await db.scalar(select(BlindChatQueueEntry).where(BlindChatQueueEntry.user_id == user_id))
    if entry is None:
        return BlindChatQueueStatusOut(status="idle")
    return await _resolve_own_entry(db, entry)
