import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, exists, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.user_lock import user_lock
from app.models.interaction import Block, Match, Report, Swipe
from app.models.profile import Photo, Profile
from app.models.user import User
from app.schemas.match import MatchOut, SwipeLimitOut, SwipeResponse
from app.services import push_service
from app.services.storage_service import build_public_url
from app.utils.db_retry import run_with_deadlock_retry
from app.utils.premium import is_premium
from app.ws.connection_manager import manager

VALID_ACTIONS = {"like", "pass", "superlike"}

# Every swipe (like/pass/superlike) counts against this — a deliberate,
# separate throttle from the Phase 17 superlike-credit system below, which
# only ever gates superlikes specifically. Calendar-day (UTC) reset, same
# convention as get_blind_chat_limit_status, not a rolling window — a fixed
# midnight boundary is what "20 free a day" actually means to a user.
SWIPE_LIMIT = 20


async def get_swipe_limit_status(db: AsyncSession, user_id: uuid.UUID) -> SwipeLimitOut:
    """Premium members skip the limit entirely (one of the real, functional
    perks premium actually grants, not just marketing copy). Everyone else
    gets SWIPE_LIMIT swipes per UTC calendar day, plus +1 if today's
    rewarded-ad bonus has been claimed (see claim_swipe_ad_bonus)."""
    profile = await db.get(Profile, user_id)
    if profile is not None and is_premium(profile.premium_until):
        return SwipeLimitOut(remaining=SWIPE_LIMIT, limit=SWIPE_LIMIT, resets_at=None, unlimited=True)

    today = datetime.now(timezone.utc).date()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    bonus_claimed_today = profile is not None and profile.swipe_bonus_ad_watched_on == today
    effective_limit = SWIPE_LIMIT + (1 if bonus_claimed_today else 0)

    count = await db.scalar(
        select(func.count())
        .select_from(Swipe)
        .where(Swipe.from_user_id == user_id, Swipe.created_at >= today_start)
    )
    remaining = max(0, effective_limit - (count or 0))
    resets_at = None
    if remaining == 0:
        resets_at = today_start + timedelta(days=1)
    return SwipeLimitOut(
        remaining=remaining,
        limit=effective_limit,
        resets_at=resets_at,
        bonus_available=not bonus_claimed_today,
    )


async def claim_swipe_ad_bonus(db: AsyncSession, user_id: uuid.UUID) -> SwipeLimitOut:
    """Grants today's +1 rewarded-ad swipe bonus — called after the client
    confirms a rewarded ad was watched to completion (EARNED_REWARD), never
    just for opening/attempting one. Mirrors
    blind_chat_service.claim_blind_chat_ad_bonus exactly, including the SSV
    gate: with AD_BONUS_REQUIRES_SSV on, this is just a status read while
    routers/ads.py's signed callback is what actually grants the bonus."""
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    if settings.ad_bonus_requires_ssv:
        return await get_swipe_limit_status(db, user_id)
    today = date.today()
    if profile.swipe_bonus_ad_watched_on != today:
        profile.swipe_bonus_ad_watched_on = today
        await db.commit()
    return await get_swipe_limit_status(db, user_id)


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

    from_profile = await db.get(Profile, from_user_id)
    if from_profile is not None and from_profile.is_suspended:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account suspended")

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
                "message": f"swipe limit reached ({SWIPE_LIMIT} per day)",
                "resets_at": limit_status.resets_at.isoformat() if limit_status.resets_at else None,
            },
        )

    async def _swipe_transaction():
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
        swipe_row = result.fetchone()
        await db.commit()
        return swipe_row

    # A swipe racing a block/other swipe between the same people can be chosen as
    # a deadlock victim by SQL Server; redoing the whole transaction is the fix.
    row = await run_with_deadlock_retry(db, _swipe_transaction)

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


mask_display_name = _mask_display_name  # public alias: chat push notifications mask the same way


def _has_peeked(m: Match, viewer_id: uuid.UUID) -> bool:
    """Whether `viewer_id` has spent their own stealth-peek credit on this
    match (services/match_service.use_blind_peek) — per-viewer, never the
    peer's flag, so this can only ever unmask the caller's own view."""
    return m.blind_peeked_by_user_a if m.user_a_id == viewer_id else m.blind_peeked_by_user_b


def _age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _build_match_out(
    m: Match, viewer_id: uuid.UUID, profile: Profile | None, photo: Photo | None
) -> MatchOut:
    other_id = m.user_b_id if m.user_a_id == viewer_id else m.user_a_id
    restricted = _is_restricted_and_waiting(m)
    display_name = profile.display_name if profile else ""
    photo_url = build_public_url(photo.gcs_object_path) if photo else None
    age = _age(profile.birth_date) if profile else None
    # Age and gender stay visible pre-reveal (product decision: not identifying
    # enough on their own to withhold, unlike name/photo) — the mobile client
    # renders gender as a symbol rather than the word while still masked.
    gender = profile.gender if profile else None
    mbti = (profile.mbti or None) if profile else None
    bio = profile.bio if profile else None
    bio2 = profile.bio2 if profile else None
    bio3 = profile.bio3 if profile else None

    viewer_peeked = _has_peeked(m, viewer_id)
    # still_anonymous drives the mutual-reveal request/accept UI, which stays
    # available even after a one-sided peek — peeking is a private shortcut
    # for the peeker alone, not a substitute for actually, honestly revealing
    # both ways. hide_identity is the narrower "does THIS viewer's own copy
    # of MatchOut need its name/photo masked" question, which peeking does
    # answer (no, not for them).
    still_anonymous = m.is_blind and not m.blind_revealed
    hide_identity = still_anonymous and not viewer_peeked
    if hide_identity:
        display_name = _mask_display_name(display_name)
        photo_url = None
        # Only the main bio survives pre-reveal — bio2/bio3 wait for the same
        # gate as name/photo now (product decision, revised from "bios are
        # never identity-sensitive").
        bio2 = None
        bio3 = None

    return MatchOut(
        id=m.id,
        other_user_id=other_id,
        other_display_name=display_name,
        other_photo_url=photo_url,
        other_age=age,
        other_gender=gender,
        other_mbti=mbti,
        other_bio=bio,
        other_bio2=bio2,
        other_bio3=bio3,
        matched_at=m.matched_at,
        is_message_restricted=restricted,
        can_send_first_message=(not restricted) or (m.restricted_to_user_id == viewer_id),
        first_message_deadline=m.first_message_deadline,
        is_active=m.is_active,
        is_blind=m.is_blind,
        blind_categories=[c for c in (m.blind_categories or "").split(",") if c],
        blind_revealed=m.blind_revealed,
        can_request_reveal=(
            still_anonymous
            and (m.blind_reveal_eligible_user_id is None or m.blind_reveal_eligible_user_id == viewer_id)
        ),
        has_incoming_reveal_request=(
            still_anonymous and m.blind_reveal_requested_by is not None and m.blind_reveal_requested_by != viewer_id
        ),
        reveal_requested_by_me=m.blind_reveal_requested_by == viewer_id,
        has_peeked=viewer_peeked,
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


FREE_PEEK_DAILY_ALLOWANCE = 1
FREE_PEEK_WINDOW = timedelta(days=1)


def _free_peek_reset_at_aware(profile: Profile) -> datetime | None:
    reset_at = profile.free_peek_reset_at
    if reset_at is not None and reset_at.tzinfo is None:
        reset_at = reset_at.replace(tzinfo=timezone.utc)
    return reset_at


def _current_free_peek_remaining(profile: Profile) -> int:
    """Read-only: what profile.free_peek_remaining WOULD be right now if the
    daily window were refreshed, without writing anything — used to show an
    accurate count on GET /profiles/me even when the window rolled over since
    the last actual peek (see routers/profiles.py). Gender-neutral (product
    decision) — the real write only ever happens inside use_blind_peek's own
    transaction, when a peek is actually spent."""
    reset_at = _free_peek_reset_at_aware(profile)
    if reset_at is None or datetime.now(timezone.utc) >= reset_at:
        return FREE_PEEK_DAILY_ALLOWANCE
    return profile.free_peek_remaining


async def use_blind_peek(db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID) -> MatchOut | None:
    """Lets `user_id` alone see the other side's real profile in a still-
    anonymous blind match — deliberately the mirror image of
    request_blind_reveal/accept_blind_reveal above: no peer consent, no WS
    event, no push, and blind_revealed never flips. Spends, in order: (1) a
    free daily peek if the user (any gender) has one left this rolling 24h
    window (refilled lazily right here — no scheduler, same
    convention as every other timed reset in this app), then (2) 1
    Profile.stealth_peek_credits. 402s only once both are exhausted.
    Idempotent — peeking again on a match already peeked just re-returns the
    current state, free (never double-charges, never re-checks either
    balance the second time)."""
    match = await db.get(Match, match_id)
    if match is None or user_id not in (match.user_a_id, match.user_b_id):
        return None
    if not match.is_blind or match.blind_revealed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not an anonymous blind match")
    if _has_peeked(match, user_id):
        return await get_match_out(db, match_id, user_id)

    # Grants and spends of the same user's credits are serialized (see
    # core/user_lock.py) so this can't interleave with a webhook grant (or
    # another spend) and lose an update — same convention as payment_service.
    async with user_lock(f"credits:{user_id}"):
        profile = await db.get(Profile, user_id)
        if profile is None:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "no stealth peek credits")

        reset_at = _free_peek_reset_at_aware(profile)
        now = datetime.now(timezone.utc)
        if reset_at is None or now >= reset_at:
            profile.free_peek_remaining = FREE_PEEK_DAILY_ALLOWANCE
            profile.free_peek_reset_at = now + FREE_PEEK_WINDOW

        if profile.free_peek_remaining > 0:
            profile.free_peek_remaining -= 1
        elif profile.stealth_peek_credits > 0:
            profile.stealth_peek_credits -= 1
        else:
            raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "no stealth peek credits")

        if match.user_a_id == user_id:
            match.blind_peeked_by_user_a = True
        else:
            match.blind_peeked_by_user_b = True
        await db.commit()

    return await get_match_out(db, match_id, user_id)


def _comma_list(value: str | None) -> list[str]:
    return [v for v in (value or "").split(",") if v]


class HideIdentityError(Exception):
    """Raised by get_matched_profile for a still-anonymous blind match — the
    router turns this into 403, distinct from the plain 404 for a match that
    doesn't exist / isn't the viewer's."""


async def get_matched_profile(db: AsyncSession, match_id: uuid.UUID, viewer_id: uuid.UUID):
    """The full profile (all photos, age, gender, interests, MBTI, ...) of the
    other side of a match — same shape discovery cards use (CandidateOut),
    reachable by tapping a match's name/photo once there's something to show:
    always for an ordinary match, only after blind_revealed for a blind one."""
    from app.schemas.discovery import CandidateOut
    from app.schemas.profile import PhotoOut
    from app.schemas.moment import MomentOut
    from app.services.discovery_service import get_photos_for_users
    from app.services.moment_service import get_moments_for_users

    m = await db.get(Match, match_id)
    if m is None or viewer_id not in (m.user_a_id, m.user_b_id):
        return None
    if m.is_blind and not m.blind_revealed and not _has_peeked(m, viewer_id):
        raise HideIdentityError()

    other_id = m.user_b_id if m.user_a_id == viewer_id else m.user_a_id
    profile = await db.get(Profile, other_id)
    if profile is None:
        return None
    photos = (await get_photos_for_users(db, [other_id])).get(other_id, [])
    moments = (await get_moments_for_users(db, [other_id])).get(other_id, [])
    return CandidateOut(
        user_id=profile.user_id,
        display_name=profile.display_name,
        age=_age(profile.birth_date),
        gender=profile.gender,
        bio=profile.bio,
        bio2=profile.bio2,
        bio3=profile.bio3,
        photos=[PhotoOut.model_validate(p) for p in photos],
        height_cm=profile.height_cm,
        occupation=profile.occupation,
        education=profile.education,
        hometown=profile.hometown,
        race_ethnicity=profile.race_ethnicity,
        religion=profile.religion,
        political_view=profile.political_view,
        smoking=profile.smoking,
        cannabis=profile.cannabis,
        exercise_frequency=profile.exercise_frequency,
        relationship_goal=profile.relationship_goal,
        wants_kids=profile.wants_kids,
        has_kids=profile.has_kids,
        interests=_comma_list(profile.interests),
        languages=_comma_list(profile.languages),
        k_content_tags=_comma_list(profile.k_content_tags),
        verified_badge=profile.verified_badge,
        face_verified=profile.face_verified,
        open_to_language_exchange=profile.open_to_language_exchange,
        moments=[MomentOut.model_validate(mo) for mo in moments],
    )


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


async def delete_match(db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Deletes the match and (via ondelete=CASCADE on every table with a
    MatchId FK — Messages, CallSessions, CoupleStories, BlindChatFeedback;
    BlindChatQueueEntry.MatchedId is ondelete=SET NULL) everything tied to
    it. Also clears the Swipe rows between the pair *unless* either side has
    reported or blocked the other — discovery excludes anyone still swiped
    on (app/services/discovery_service.py's already_swiped), so clearing
    them is what actually lets the two people match again later; a report or
    block means that should stay closed instead. Returns False only if the
    match doesn't exist or user_id isn't a participant (-> 404 at the
    router)."""
    match = await db.get(Match, match_id)
    if match is None or user_id not in (match.user_a_id, match.user_b_id):
        return False
    other_id = match.user_b_id if match.user_a_id == user_id else match.user_a_id

    # Two separate single-table scalar checks, not one exists() combining both
    # tables — MSSQL doesn't accept a bare "SELECT EXISTS(...)" the way
    # Postgres/MySQL do, and a single exists().where() referencing two
    # unrelated tables produces an (also broken) unjoined cartesian product.
    reported = await db.scalar(
        select(Report.id)
        .where(
            or_(
                and_(Report.reporter_id == user_id, Report.reported_id == other_id),
                and_(Report.reporter_id == other_id, Report.reported_id == user_id),
            )
        )
        .limit(1)
    )
    blocked = await db.scalar(
        select(Block.id)
        .where(
            or_(
                and_(Block.blocker_id == user_id, Block.blocked_id == other_id),
                and_(Block.blocker_id == other_id, Block.blocked_id == user_id),
            )
        )
        .limit(1)
    )
    reported_or_blocked = reported is not None or blocked is not None

    await db.delete(match)
    swipe_pair = or_(
        and_(Swipe.from_user_id == user_id, Swipe.to_user_id == other_id),
        and_(Swipe.from_user_id == other_id, Swipe.to_user_id == user_id),
    )
    if reported_or_blocked:
        # A match existing at all means BOTH sides already have a "like"/
        # "superlike" swipe on record — simply leaving those in place would
        # let a single new like from either side immediately re-match them
        # again (record_swipe just checks for an existing reciprocal like),
        # undoing the whole point of a report/block. Neutralize them to
        # "pass" instead of deleting: discovery keeps excluding the pair
        # (already_swiped doesn't care about the action) and neither side's
        # like can find a reciprocal anymore, without erasing the record.
        await db.execute(update(Swipe).where(swipe_pair).values(action="pass"))
    else:
        await db.execute(delete(Swipe).where(swipe_pair))
    await db.commit()
    return True


async def list_matches(db: AsyncSession, user_id: uuid.UUID) -> list[MatchOut]:
    await expire_stale_matches(db, user_id)

    # Unlike the old behavior (WHERE is_active only), expired matches are
    # still returned here rather than silently vanishing — the mobile chat
    # list renders them as a distinct grayed-out "Expired" row instead of
    # dropping them, so a match that timed out is still visible history,
    # just no longer chattable (chat_service blocks sending into it).
    # A blocked pair (either direction) never shows up in the chat list.
    blocked_pair = exists().where(
        or_(
            and_(Block.blocker_id == Match.user_a_id, Block.blocked_id == Match.user_b_id),
            and_(Block.blocker_id == Match.user_b_id, Block.blocked_id == Match.user_a_id),
        )
    )
    rows = (
        await db.execute(
            select(Match).where(
                or_(Match.user_a_id == user_id, Match.user_b_id == user_id),
                ~blocked_pair,
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
