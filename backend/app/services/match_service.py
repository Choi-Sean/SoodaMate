import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Match, Swipe
from app.models.profile import Photo, Profile
from app.schemas.match import MatchOut, SwipeLimitOut, SwipeResponse
from app.services import push_service
from app.services.storage_service import build_public_url

VALID_ACTIONS = {"like", "pass", "superlike"}

# Every swipe (like/pass/superlike) counts against this — a deliberate,
# separate throttle from the Phase 17 superlike-credit system below, which
# only ever gates superlikes specifically.
SWIPE_LIMIT = 20
SWIPE_LIMIT_WINDOW = timedelta(hours=6)


async def get_swipe_limit_status(db: AsyncSession, user_id: uuid.UUID) -> SwipeLimitOut:
    """Rolling window, not a fixed clock-aligned one: your 21st swipe is
    blocked until your oldest swipe in the last 6h ages out, not until a
    fixed boundary — so resets_at is that oldest swipe's timestamp + 6h."""
    window_start = datetime.now(timezone.utc) - SWIPE_LIMIT_WINDOW
    timestamps = (
        await db.execute(
            select(Swipe.created_at)
            .where(Swipe.from_user_id == user_id, Swipe.created_at >= window_start)
            .order_by(Swipe.created_at.asc())
        )
    ).scalars().all()

    remaining = max(0, SWIPE_LIMIT - len(timestamps))
    resets_at = None
    if remaining == 0:
        oldest = timestamps[0]
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        resets_at = oldest + SWIPE_LIMIT_WINDOW
    return SwipeLimitOut(remaining=remaining, limit=SWIPE_LIMIT, resets_at=resets_at)


async def _consume_superlike_allowance(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Phase 17: 1 free superlike/day, then consumes purchased credits, else
    402. Runs inside the same transaction as the swipe itself."""
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")

    today = date.today()
    if profile.free_superlike_used_on != today:
        profile.free_superlike_used_on = today
    elif profile.superlike_credits > 0:
        profile.superlike_credits -= 1
    else:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "no superlikes left today")


async def record_swipe(
    db: AsyncSession, from_user_id: uuid.UUID, to_user_id: uuid.UUID, action: str
) -> SwipeResponse:
    if action not in VALID_ACTIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid action")
    if from_user_id == to_user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot swipe on yourself")

    limit_status = await get_swipe_limit_status(db, from_user_id)
    if limit_status.remaining <= 0:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            {
                "message": f"swipe limit reached ({SWIPE_LIMIT} per {int(SWIPE_LIMIT_WINDOW.total_seconds() // 3600)}h)",
                "resets_at": limit_status.resets_at.isoformat() if limit_status.resets_at else None,
            },
        )

    if action == "superlike":
        await _consume_superlike_allowance(db, from_user_id)

    # The core swipe/match transaction lives in sp_RecordSwipe (see
    # infra/mssql/stored_procedures.sql) — upserts the Swipe row, checks for
    # a reciprocal like/superlike, and on mutual match creates the Match row
    # with the Phase 14 Bumble first-message restriction computed inline.
    result = await db.execute(
        text("EXEC sp_RecordSwipe @FromUserId=:from_id, @ToUserId=:to_id, @Action=:action"),
        {"from_id": from_user_id, "to_id": to_user_id, "action": action},
    )
    row = result.fetchone()
    await db.commit()

    if row.Blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "cannot interact with this user")
    if not row.Matched:
        return SwipeResponse(matched=False)

    await push_service.send_match_notification(db, from_user_id, row.MatchId)
    await push_service.send_match_notification(db, to_user_id, row.MatchId)

    return SwipeResponse(matched=True, match_id=row.MatchId)


def _is_restricted_and_waiting(match: Match) -> bool:
    return match.restricted_to_user_id is not None and not match.first_message_sent


async def expire_stale_matches(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Phase 14 lazy expiry: flips is_active=False for any of this user's
    matches whose first-message deadline passed with nothing sent. No
    scheduler exists (or is planned) — every real touchpoint (list, WS
    connect-time send/read) calls this or the single-match equivalent in
    chat_service.get_active_match_for_user instead."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(Match)
        .where(
            # Column truthiness, not .is_(True)/.is_(False) — MSSQL has no
            # IS TRUE/IS FALSE syntax (only IS NULL).
            Match.is_active,
            ~Match.first_message_sent,
            Match.first_message_deadline.isnot(None),
            Match.first_message_deadline <= now,
            or_(Match.user_a_id == user_id, Match.user_b_id == user_id),
        )
        .values(is_active=False)
    )
    await db.commit()


async def list_matches(db: AsyncSession, user_id: uuid.UUID) -> list[MatchOut]:
    await expire_stale_matches(db, user_id)

    rows = (
        await db.execute(
            select(Match).where(
                Match.is_active,
                or_(Match.user_a_id == user_id, Match.user_b_id == user_id),
            ).order_by(Match.matched_at.desc())
        )
    ).scalars().all()

    other_ids = [m.user_b_id if m.user_a_id == user_id else m.user_a_id for m in rows]
    profiles_by_user = {}
    first_photo_by_user: dict[uuid.UUID, Photo] = {}
    if other_ids:
        profile_rows = (
            await db.execute(select(Profile).where(Profile.user_id.in_(other_ids)))
        ).scalars()
        profiles_by_user = {p.user_id: p for p in profile_rows}

        photo_rows = (
            await db.execute(
                # media_type == "photo" only — a chat-list avatar can't show
                # a video frame, so the one video slot a profile can have is
                # skipped in favor of its first real photo.
                select(Photo)
                .where(Photo.user_id.in_(other_ids), Photo.media_type == "photo")
                .order_by(Photo.user_id, Photo.position)
            )
        ).scalars()
        for photo in photo_rows:
            first_photo_by_user.setdefault(photo.user_id, photo)

    out = []
    for m in rows:
        other_id = m.user_b_id if m.user_a_id == user_id else m.user_a_id
        profile = profiles_by_user.get(other_id)
        photo = first_photo_by_user.get(other_id)
        restricted = _is_restricted_and_waiting(m)
        out.append(
            MatchOut(
                id=m.id,
                other_user_id=other_id,
                other_display_name=profile.display_name if profile else "",
                other_photo_url=build_public_url(photo.gcs_object_path) if photo else None,
                matched_at=m.matched_at,
                is_message_restricted=restricted,
                can_send_first_message=(not restricted) or (m.restricted_to_user_id == user_id),
                first_message_deadline=m.first_message_deadline,
            )
        )
    return out
