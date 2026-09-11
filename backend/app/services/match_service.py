import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Match, Swipe
from app.models.profile import Photo, Profile
from app.models.user import User
from app.schemas.match import MatchOut, SwipeLimitOut, SwipeResponse
from app.services import push_service
from app.services.storage_service import build_public_url
from app.utils.premium import is_premium
from app.ws.connection_manager import manager

VALID_ACTIONS = {"like", "pass", "superlike"}

# Every swipe (like/pass/superlike) counts against this — a deliberate,
# separate throttle from the Phase 17 superlike-credit system below, which
# only ever gates superlikes specifically.
SWIPE_LIMIT = 20
SWIPE_LIMIT_WINDOW = timedelta(hours=6)


async def get_swipe_limit_status(db: AsyncSession, user_id: uuid.UUID) -> SwipeLimitOut:
    """Rolling window, not a fixed clock-aligned one: your 21st swipe is
    blocked until your oldest swipe in the last 6h ages out, not until a
    fixed boundary — so resets_at is that oldest swipe's timestamp + 6h.
    Premium members skip the limit entirely (one of the real, functional
    perks premium actually grants, not just marketing copy)."""
    profile = await db.get(Profile, user_id)
    if profile is not None and is_premium(profile.premium_until):
        return SwipeLimitOut(remaining=SWIPE_LIMIT, limit=SWIPE_LIMIT, resets_at=None, unlimited=True)

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

    # The target's card may have been fetched well before this swipe lands
    # (the discovery deck is cached client-side) — if that account was
    # deleted in the meantime, sp_RecordSwipe's Swipe insert would blow up on
    # the FK with a 500 instead of a clean, expected 404. Same guard as
    # safety.py's block_user/report_user.
    if await db.get(User, to_user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

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
        if action in ("like", "superlike"):
            await push_service.send_like_notification(db, to_user_id, superlike=action == "superlike")
        return SwipeResponse(matched=False)

    await push_service.send_match_notification(db, from_user_id, row.MatchId)
    await push_service.send_match_notification(db, to_user_id, row.MatchId)

    return SwipeResponse(matched=True, match_id=row.MatchId)


def _is_restricted_and_waiting(match: Match) -> bool:
    return match.restricted_to_user_id is not None and not match.first_message_sent


def _mask_display_name(name: str) -> str:
    """First character (uppercased if it's a Latin letter — a no-op
    otherwise, e.g. Korean) + "***", always — never the real length, so a
    blind-chat match's name reveals nothing beyond "starts with this
    character" until blind_revealed flips."""
    return f"{name[0].upper()}***" if name else "?***"


def _build_match_out(
    m: Match, viewer_id: uuid.UUID, profile: Profile | None, photo: Photo | None
) -> MatchOut:
    other_id = m.user_b_id if m.user_a_id == viewer_id else m.user_a_id
    restricted = _is_restricted_and_waiting(m)
    display_name = profile.display_name if profile else ""
    photo_url = build_public_url(photo.gcs_object_path) if photo else None

    hide_identity = m.is_blind and not m.blind_revealed
    if hide_identity:
        display_name = _mask_display_name(display_name)
        photo_url = None

    return MatchOut(
        id=m.id,
        other_user_id=other_id,
        other_display_name=display_name,
        other_photo_url=photo_url,
        matched_at=m.matched_at,
        is_message_restricted=restricted,
        can_send_first_message=(not restricted) or (m.restricted_to_user_id == viewer_id),
        first_message_deadline=m.first_message_deadline,
        is_active=m.is_active,
        is_blind=m.is_blind,
        blind_categories=[c for c in (m.blind_categories or "").split(",") if c],
        blind_revealed=m.blind_revealed,
        can_request_reveal=(
            hide_identity
            and (m.blind_reveal_eligible_user_id is None or m.blind_reveal_eligible_user_id == viewer_id)
        ),
        has_incoming_reveal_request=(
            hide_identity and m.blind_reveal_requested_by is not None and m.blind_reveal_requested_by != viewer_id
        ),
        reveal_requested_by_me=m.blind_reveal_requested_by == viewer_id,
    )


async def request_blind_reveal(db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID) -> MatchOut | None:
    """Returns None only if the match doesn't exist or user_id isn't a
    participant (-> 404 at the router); raises 400/403 for a valid match in
    the wrong state, mirroring the pattern used elsewhere in this file."""
    match = await db.get(Match, match_id)
    if match is None or user_id not in (match.user_a_id, match.user_b_id):
        return None
    if not match.is_blind or match.blind_revealed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not an open blind chat")
    if match.blind_reveal_eligible_user_id is not None and match.blind_reveal_eligible_user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the eligible side can request a reveal")

    match.blind_reveal_requested_by = user_id
    await db.commit()

    peer_id = match.user_b_id if match.user_a_id == user_id else match.user_a_id
    delivered = await manager.send_to_user(peer_id, {"type": "blind_reveal_requested", "match_id": str(match_id)})
    if not delivered:
        await push_service.send_blind_reveal_requested_notification(db, peer_id, match_id)
    return await get_match_out(db, match_id, user_id)


async def accept_blind_reveal(db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID) -> MatchOut | None:
    match = await db.get(Match, match_id)
    if match is None or user_id not in (match.user_a_id, match.user_b_id):
        return None
    if not match.is_blind or match.blind_revealed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not an open blind chat")
    if match.blind_reveal_requested_by is None or match.blind_reveal_requested_by == user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no pending reveal request from the other side")

    match.blind_revealed = True
    await db.commit()

    peer_id = match.blind_reveal_requested_by
    delivered = await manager.send_to_user(peer_id, {"type": "blind_reveal_accepted", "match_id": str(match_id)})
    if not delivered:
        await push_service.send_blind_reveal_accepted_notification(db, peer_id, match_id)
    return await get_match_out(db, match_id, user_id)


async def get_match_out(db: AsyncSession, match_id: uuid.UUID, viewer_id: uuid.UUID) -> MatchOut | None:
    """Single-match equivalent of list_matches, for endpoints that mutate
    one match (blind-reveal request/accept) and want to hand back its fresh
    state without the caller re-deriving MatchOut by hand."""
    m = await db.get(Match, match_id)
    if m is None or viewer_id not in (m.user_a_id, m.user_b_id):
        return None
    other_id = m.user_b_id if m.user_a_id == viewer_id else m.user_a_id
    profile = await db.get(Profile, other_id)
    photo = await db.scalar(
        select(Photo)
        .where(Photo.user_id == other_id, Photo.media_type == "photo")
        .order_by(Photo.position)
        .limit(1)
    )
    return _build_match_out(m, viewer_id, profile, photo)


async def expire_stale_matches(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Lazy expiry, mirroring chat_service._is_expired's rule: flips
    is_active=False for any of this user's matches where either (a)
    nobody ever sent the first message and the Phase 14 deadline passed,
    or (b) a conversation is underway but nobody has replied to the most
    recent message within 24h. No scheduler exists (or is planned) —
    every real touchpoint (list, WS connect-time send/read) calls this or
    the single-match equivalent in chat_service.get_active_match_for_user
    instead."""
    now = datetime.now(timezone.utc)
    reply_cutoff = now - timedelta(hours=24)
    await db.execute(
        update(Match)
        .where(
            # Column truthiness, not .is_(True)/.is_(False) — MSSQL has no
            # IS TRUE/IS FALSE syntax (only IS NULL).
            Match.is_active,
            or_(
                and_(
                    ~Match.first_message_sent,
                    Match.first_message_deadline.isnot(None),
                    Match.first_message_deadline <= now,
                ),
                and_(
                    Match.first_message_sent,
                    func.coalesce(Match.last_activity_at, Match.matched_at) <= reply_cutoff,
                ),
            ),
            or_(Match.user_a_id == user_id, Match.user_b_id == user_id),
        )
        .values(is_active=False)
    )
    await db.commit()


async def list_matches(db: AsyncSession, user_id: uuid.UUID) -> list[MatchOut]:
    await expire_stale_matches(db, user_id)

    # Unlike the old behavior (WHERE is_active only), expired matches are
    # still returned here rather than silently vanishing — the mobile chat
    # list renders them as a distinct grayed-out "Expired" row instead of
    # dropping them, so a match that timed out is still visible history,
    # just no longer chattable (chat_service blocks sending into it).
    rows = (
        await db.execute(
            select(Match).where(
                or_(Match.user_a_id == user_id, Match.user_b_id == user_id),
            ).order_by(Match.is_active.desc(), Match.matched_at.desc())
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
        out.append(_build_match_out(m, user_id, profile, photo))
    return out
