import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.blind_chat import BlindChatQueueEntry
from app.models.blind_chat_feedback import BlindChatFeedback
from app.models.interaction import Block, Match
from app.models.profile import Profile
from app.models.user import User
from app.schemas.match import (
    BlindChatFeedbackCreate,
    BlindChatFeedbackOut,
    BlindChatLimitOut,
    BlindChatQueueStatusOut,
)
from app.services import llm_match_service, push_service
from app.utils.mbti import compatible_types
from app.utils.premium import is_premium
from app.utils.upsert import try_insert
from app.ws.connection_manager import manager

# Added to the AI Match ranking score when the candidate's MBTI is the
# viewer's single best-match type (utils.mbti) — comparable in weight to a
# shared interest/K-content tag (2.0 each), a bit above, since it's a
# deliberate "compatible personality" signal. Regular (queue) matching never
# considers MBTI at all; only AI Match does.
MBTI_COMPATIBILITY_BONUS = 3.0

# Free members get this many blind-chat matches per calendar day (counted
# from Match rows, same "count real rows in a window" approach as
# match_service.SWIPE_LIMIT — a full-day window has plenty of margin against
# the sandbox/DB clock skew that ruled out short time-window checks
# elsewhere in this feature, see BlindChatQueueEntry.matched_id's docstring).
# Premium members and Unlimited Matching purchasers skip this entirely.
BLIND_CHAT_FREE_DAILY_LIMIT = 5

# A queue entry older than this is treated as abandoned (app closed/crashed/
# backgrounded without hitting Cancel — there's no client-side cleanup on
# unmount) and excluded from matching, not just stale-looking in a UI. Found
# empirically: with category no longer narrowing candidates (see
# _compatibility_filters), one real leftover entry from manual testing was
# old enough to out-rank every genuinely-waiting candidate on `ORDER BY
# created_at ASC` and silently absorb a match meant for someone else.
STALE_QUEUE_ENTRY = timedelta(minutes=15)


def _age_to_birth_date_bounds(min_age: int, max_age: int) -> tuple[date, date]:
    today = date.today()
    max_birth_date = today.replace(year=today.year - min_age)
    min_birth_date = today.replace(year=today.year - max_age - 1) + timedelta(days=1)
    return min_birth_date, max_birth_date


def _age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _haversine_km(lat1, lng1, lat2, lng2):
    """Same portable formula as discovery_service._haversine_km — duplicated
    locally per this module's established small-helper convention."""
    r = 6371.0
    lat1r, lat2r = func.radians(lat1), func.radians(lat2)
    dlat = func.radians(lat2 - lat1)
    dlng = func.radians(lng2 - lng1)
    a = func.power(func.sin(dlat / 2), 2) + func.cos(lat1r) * func.cos(lat2r) * func.power(
        func.sin(dlng / 2), 2
    )
    return r * 2 * func.asin(func.sqrt(a))


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


def is_unlimited_matching_active(profile: Profile) -> bool:
    """Premium members already get this for free — Unlimited Matching is a
    narrower, cheaper standalone purchase for someone who only wants that
    one perk (see payment_service.PRODUCTS' unlimited_matching_* entries)."""
    if is_premium(profile.premium_until):
        return True
    until = profile.unlimited_matching_until
    if until is None:
        return False
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    return until > datetime.now(timezone.utc)


async def get_blind_chat_limit_status(db: AsyncSession, user_id: uuid.UUID) -> BlindChatLimitOut:
    profile = await db.get(Profile, user_id)
    if profile is not None and is_unlimited_matching_active(profile):
        return BlindChatLimitOut(remaining=BLIND_CHAT_FREE_DAILY_LIMIT, limit=BLIND_CHAT_FREE_DAILY_LIMIT, unlimited=True)

    today = datetime.now(timezone.utc).date()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    bonus_claimed_today = profile is not None and profile.blind_chat_bonus_ad_watched_on == today
    effective_limit = BLIND_CHAT_FREE_DAILY_LIMIT + (1 if bonus_claimed_today else 0)
    count = await db.scalar(
        select(func.count())
        .select_from(Match)
        .where(
            # Plain column truthiness, not .is_(True) — MSSQL has no IS
            # TRUE/IS FALSE syntax (only IS NULL), see discovery_service's
            # same note.
            Match.is_blind,
            Match.matched_at >= today_start,
            or_(Match.user_a_id == user_id, Match.user_b_id == user_id),
        )
    )
    remaining = max(0, effective_limit - (count or 0))
    resets_at = None
    if remaining == 0:
        resets_at = today_start + timedelta(days=1)
    return BlindChatLimitOut(
        remaining=remaining,
        limit=effective_limit,
        resets_at=resets_at,
        bonus_available=not bonus_claimed_today,
    )


async def claim_blind_chat_ad_bonus(db: AsyncSession, user_id: uuid.UUID) -> BlindChatLimitOut:
    """Grants today's +1 rewarded-ad bonus match — called after the client
    confirms a rewarded ad was watched to completion (EARNED_REWARD), never
    just for opening/attempting one. Idempotent per day: watching a second
    ad the same day is harmless, just doesn't stack (see
    Profile.blind_chat_bonus_ad_watched_on's docstring for why this is
    capped at 1/day rather than unlimited)."""
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    if settings.ad_bonus_requires_ssv:
        # The bonus is granted only by AdMob's signed callback (routers/ads.py);
        # a client saying "I watched it" proves nothing, so this is now just a
        # status read the app can poll while the callback is in flight.
        return await get_blind_chat_limit_status(db, user_id)
    today = datetime.now(timezone.utc).date()
    if profile.blind_chat_bonus_ad_watched_on != today:
        profile.blind_chat_bonus_ad_watched_on = today
        await db.commit()
    return await get_blind_chat_limit_status(db, user_id)


def _compatibility_filters(
    user_id: uuid.UUID,
    viewer_profile: Profile,
    categories: list[str],
    gender: str | None,
    min_age: int | None,
    max_age: int | None,
):
    """Shared WHERE-clause pieces for both the live-queue FIFO match
    (_find_waiting_partner) and the AI-scored match (find_ai_match) — same
    mutual gender/age/distance compatibility rules either way, only the
    ordering differs.

    gender/min_age/max_age/max_distance_km are this VIEWER's optional
    per-session choices (see BlindChatQueueRequest) and take precedence over
    their own profile-level defaults for this call only — including
    "all"/a different gender than the profile's interested_in, since the
    choice made on the match screen (which the client defaults to the profile
    value and confirms when it differs) is what the user actually wants for
    this session. The candidate side of every comparison below must instead read from
    BlindChatQueueEntry's own stored *_filter columns (falling back to the
    candidate's profile default via COALESCE when they didn't set one) —
    never straight from Profile — because the candidate already committed
    their own session's preferences to that row when *they* joined, and this
    viewer's search is what finds and matches against it later. Reading the
    candidate's live Profile columns instead would silently ignore whatever
    override the candidate's own session actually asked for.

    categories is NOT a hard filter here — with a small early user base,
    requiring an overlapping topic left most queues matching nobody at all.
    It's still used to compute blind_categories (shared-topic display in the
    match) and find_ai_match's scoring. MBTI is deliberately NOT a filter
    either (it used to be, via an "mbti_match" category — two same-type
    testers could never match): regular matching ignores MBTI entirely, and
    only AI Match weighs it (see _compatibility_score / llm_match_service)."""
    lo, hi = min_age or viewer_profile.min_age_pref, max_age or viewer_profile.max_age_pref
    viewer_min_birth, viewer_max_birth = _age_to_birth_date_bounds(lo, hi)
    viewer_age = _age(viewer_profile.birth_date)

    effective_interested_in = gender or viewer_profile.interested_in
    gender_filters = [Profile.gender == effective_interested_in] if effective_interested_in != "all" else []

    candidate_interested_in = func.coalesce(BlindChatQueueEntry.gender_filter, Profile.interested_in)
    mutual_interest = or_(candidate_interested_in == "all", candidate_interested_in == viewer_profile.gender)

    candidate_min_age = func.coalesce(BlindChatQueueEntry.min_age_filter, Profile.min_age_pref)
    candidate_max_age = func.coalesce(BlindChatQueueEntry.max_age_filter, Profile.max_age_pref)

    blocked_either_direction = select(Block.id).where(
        or_(
            and_(Block.blocker_id == user_id, Block.blocked_id == BlindChatQueueEntry.user_id),
            and_(Block.blocker_id == BlindChatQueueEntry.user_id, Block.blocked_id == user_id),
        )
    ).exists()

    return [
        BlindChatQueueEntry.user_id != user_id,
        BlindChatQueueEntry.matched_id.is_(None),
        BlindChatQueueEntry.created_at >= datetime.now(timezone.utc) - STALE_QUEUE_ENTRY,
        ~User.is_banned,
        User.is_active,
        ~Profile.is_suspended,
        mutual_interest,
        *gender_filters,
        Profile.birth_date >= viewer_min_birth,
        Profile.birth_date <= viewer_max_birth,
        candidate_min_age <= viewer_age,
        candidate_max_age >= viewer_age,
        ~blocked_either_direction,
    ]


def _distance_filters(viewer_profile: Profile, max_distance_km: int | None) -> list:
    """Applied from both sides independently — None (no override, on either
    side) means that side places no distance constraint at all, so two
    people who both left it unset are never distance-filtered. Plain Python
    `if`s (not SQL) decide whether each half even applies, since
    viewer_profile's own location is a fixed value for this whole query, not
    a per-candidate-row column."""
    filters = []
    has_viewer_location = viewer_profile.location_lat is not None and viewer_profile.location_lng is not None

    if max_distance_km and has_viewer_location:
        dist = _haversine_km(
            viewer_profile.location_lat, viewer_profile.location_lng, Profile.location_lat, Profile.location_lng
        )
        filters.append(or_(Profile.location_lat.is_(None), dist <= max_distance_km))

    if has_viewer_location:
        dist_reverse = _haversine_km(
            Profile.location_lat, Profile.location_lng, viewer_profile.location_lat, viewer_profile.location_lng
        )
        filters.append(
            or_(BlindChatQueueEntry.max_distance_km_filter.is_(None), dist_reverse <= BlindChatQueueEntry.max_distance_km_filter)
        )
    return filters


async def _find_waiting_partner(
    db: AsyncSession,
    user: User,
    viewer_profile: Profile,
    categories: list[str],
    gender: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    max_distance_km: int | None = None,
) -> tuple[BlindChatQueueEntry, Profile] | None:
    filters = _compatibility_filters(user.id, viewer_profile, categories, gender, min_age, max_age)
    filters += _distance_filters(viewer_profile, max_distance_km)

    stmt = (
        select(BlindChatQueueEntry, Profile)
        .join(Profile, Profile.user_id == BlindChatQueueEntry.user_id)
        .join(User, User.id == BlindChatQueueEntry.user_id)
        .where(*filters)
        .order_by(BlindChatQueueEntry.created_at.asc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    return (row[0], row[1]) if row else None


def _shared_tags(a: str | None, b: str | None) -> set[str]:
    if not a or not b:
        return set()
    return set(a.split(",")) & set(b.split(","))


def _compatibility_score(viewer_profile: Profile, candidate_profile: Profile, shared_categories: set[str]) -> float:
    """Deterministic, template-driven score — no LLM call, no external
    API/cost, same "AI-adjacent but actually just structured-data scoring"
    approach as icebreaker_service.get_icebreaker. Weighted sum of shared
    tag counts (K-content/interests/languages count double — a stronger
    day-to-day compatibility signal than a shared blind-chat category alone)
    plus an MBTI-compatibility bonus and bonuses for age and distance
    proximity."""
    score = len(shared_categories) * 1.0
    score += len(_shared_tags(viewer_profile.k_content_tags, candidate_profile.k_content_tags)) * 2.0
    score += len(_shared_tags(viewer_profile.interests, candidate_profile.interests)) * 2.0
    score += len(_shared_tags(viewer_profile.languages, candidate_profile.languages)) * 1.5
    if viewer_profile.open_to_language_exchange and candidate_profile.open_to_language_exchange:
        score += 1.0
    candidate_mbti = (candidate_profile.mbti or "").upper()
    if candidate_mbti and candidate_mbti in compatible_types(viewer_profile.mbti):
        score += MBTI_COMPATIBILITY_BONUS

    age_gap = abs(_age(viewer_profile.birth_date) - _age(candidate_profile.birth_date))
    score += max(0.0, 3.0 - age_gap * 0.3)

    if (
        viewer_profile.location_lat is not None
        and viewer_profile.location_lng is not None
        and candidate_profile.location_lat is not None
        and candidate_profile.location_lng is not None
    ):
        # Cheap Python-side approximation (no need for the SQL haversine
        # helper here — candidates are already fetched into memory for
        # scoring) — good enough to rank nearby vs. far, not for display.
        dlat = candidate_profile.location_lat - viewer_profile.location_lat
        dlng = candidate_profile.location_lng - viewer_profile.location_lng
        rough_km = ((dlat * 111) ** 2 + (dlng * 88) ** 2) ** 0.5
        score += max(0.0, 2.0 - rough_km / 50)

    return score


async def find_ai_match(
    db: AsyncSession,
    user: User,
    viewer_profile: Profile,
    categories: list[str],
    gender: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    max_distance_km: int | None = None,
) -> tuple[BlindChatQueueEntry, Profile] | None:
    """Consumes 1 ai_match_credit (checked by the router before calling this)
    to instantly pair with the best currently-waiting candidate, rather than
    the live queue's plain FIFO order. Deliberately scoped to the existing
    waiting pool (not every eligible user in the app) so both sides have
    already opted into blind chat; nobody is pulled into a match they never
    asked for.

    Two-stage ranking: _compatibility_score (tags/age/distance) always runs
    first and picks the shortlist order — cheap, deterministic, and the
    final answer whenever the LLM path is unconfigured or fails. When
    ANTHROPIC_API_KEY *is* set, llm_match_service.pick_best_candidate gets a
    shot at re-ranking just that shortlist using profile text, the viewer's
    own message tone, and candidates' past-partner feedback — signals the
    tag-overlap score can't see at all."""
    # Same session-level gender/age/distance choices as a regular queue join
    # (they take precedence over the profile defaults) — the AI only picks
    # among candidates who already pass the exact same hard filters.
    filters = _compatibility_filters(user.id, viewer_profile, categories, gender, min_age, max_age)
    filters += _distance_filters(viewer_profile, max_distance_km)
    stmt = (
        select(BlindChatQueueEntry, Profile)
        .join(Profile, Profile.user_id == BlindChatQueueEntry.user_id)
        .join(User, User.id == BlindChatQueueEntry.user_id)
        .where(*filters)
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return None

    def score_row(row):
        entry, profile = row
        shared = set(categories) & set(entry.categories.split(","))
        return _compatibility_score(viewer_profile, profile, shared)

    ranked = sorted(rows, key=score_row, reverse=True)

    shortlist = []
    for entry, profile in ranked[: llm_match_service.MAX_CANDIDATES]:
        avg_rating, top_tags = await get_feedback_summary(db, entry.user_id)
        shortlist.append((profile, avg_rating, top_tags))

    llm_index = await llm_match_service.pick_best_candidate(db, viewer_profile, shortlist)
    chosen = ranked[llm_index] if llm_index is not None else ranked[0]
    return chosen[0], chosen[1]


async def _create_match(
    db: AsyncSession, user: User, viewer_profile: Profile, categories: list[str], partner_entry, partner_profile
) -> Match:
    shared = sorted(set(categories) & set(partner_entry.categories.split(",")))

    ordered = sorted(
        [(user.id, viewer_profile), (partner_entry.user_id, partner_profile)], key=lambda t: str(t[0])
    )
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

    return match


async def join_queue(
    db: AsyncSession,
    user: User,
    viewer_profile: Profile,
    categories: list[str],
    gender: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    max_distance_km: int | None = None,
) -> BlindChatQueueStatusOut:
    existing = await db.scalar(select(BlindChatQueueEntry).where(BlindChatQueueEntry.user_id == user.id))
    if existing is not None:
        # Already waiting: either still waiting (idempotent no-op — cancel
        # first to change categories), or someone else's queue call already
        # claimed this entry for a match since the caller last checked.
        return await _resolve_own_entry(db, existing)

    limit_status = await get_blind_chat_limit_status(db, user.id)
    if limit_status.remaining <= 0:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            {
                "message": f"blind chat match limit reached ({BLIND_CHAT_FREE_DAILY_LIMIT} per day)",
                "resets_at": limit_status.resets_at.isoformat() if limit_status.resets_at else None,
            },
        )

    found = await _find_waiting_partner(db, user, viewer_profile, categories, gender, min_age, max_age, max_distance_km)
    if found is None:
        db.add(
            BlindChatQueueEntry(
                user_id=user.id,
                categories=",".join(categories),
                # Persisted so a *later* joiner's search (which finds and
                # matches against this row) applies this session's overrides
                # too — see _compatibility_filters' docstring.
                gender_filter=gender,
                min_age_filter=min_age,
                max_age_filter=max_age,
                max_distance_km_filter=max_distance_km,
            )
        )
        await db.commit()
        return BlindChatQueueStatusOut(status="waiting")

    partner_entry, partner_profile = found
    match = await _create_match(db, user, viewer_profile, categories, partner_entry, partner_profile)
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


async def use_ai_match(
    db: AsyncSession,
    user: User,
    viewer_profile: Profile,
    categories: list[str],
    gender: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    max_distance_km: int | None = None,
) -> Match | None:
    """Router-facing entry point: consumes 1 ai_match_credit and returns the
    freshly created Match, or returns None (credit left untouched — see
    schemas.match.AiMatchOut) if nobody compatible is currently waiting.
    Deliberately does NOT check the daily free-match limit — a purchased
    credit already implies "I've hit or don't care about the free cap.\""""
    if viewer_profile.ai_match_credits <= 0:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "no AI match credits left")

    found = await find_ai_match(
        db, user, viewer_profile, categories, gender, min_age, max_age, max_distance_km
    )
    if found is None:
        return None

    viewer_profile.ai_match_credits -= 1
    partner_entry, partner_profile = found
    return await _create_match(db, user, viewer_profile, categories, partner_entry, partner_profile)


async def get_queue_status(db: AsyncSession, user_id: uuid.UUID) -> BlindChatQueueStatusOut:
    entry = await db.scalar(select(BlindChatQueueEntry).where(BlindChatQueueEntry.user_id == user_id))
    if entry is None:
        return BlindChatQueueStatusOut(status="idle")
    return await _resolve_own_entry(db, entry)


def _feedback_out(row: BlindChatFeedback) -> BlindChatFeedbackOut:
    return BlindChatFeedbackOut(
        rating=row.rating,
        tags=[t for t in row.tags.split(",") if t],
        comment=row.comment,
    )


async def submit_blind_chat_feedback(
    db: AsyncSession, match_id: uuid.UUID, rater_user_id: uuid.UUID, body: BlindChatFeedbackCreate
) -> BlindChatFeedbackOut | None:
    """Returns None only if the match doesn't exist or rater_user_id isn't a
    participant (-> 404 at the router), mirroring request_blind_reveal's own
    convention. Unlike that flow, feedback is allowed on any blind match
    regardless of is_active/blind_revealed — a stale or already-revealed
    chat is still one you can rate. Re-submitting overwrites the rater's
    prior feedback for this match rather than erroring (try_insert first,
    UPDATE on the unique-constraint miss — same portable-upsert convention
    as everywhere else in this codebase that needs ON CONFLICT)."""
    match = await db.get(Match, match_id)
    if match is None or rater_user_id not in (match.user_a_id, match.user_b_id):
        return None
    if not match.is_blind:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a blind chat match")

    rated_user_id = match.user_b_id if match.user_a_id == rater_user_id else match.user_a_id
    tags_csv = ",".join(body.tags)

    row = BlindChatFeedback(
        match_id=match_id,
        rater_user_id=rater_user_id,
        rated_user_id=rated_user_id,
        rating=body.rating,
        tags=tags_csv,
        comment=body.comment,
    )
    if not await try_insert(db, row):
        existing = await db.scalar(
            select(BlindChatFeedback).where(
                BlindChatFeedback.match_id == match_id,
                BlindChatFeedback.rater_user_id == rater_user_id,
            )
        )
        existing.rating = body.rating
        existing.tags = tags_csv
        existing.comment = body.comment
        row = existing
    await db.commit()
    await db.refresh(row)
    return _feedback_out(row)


async def get_feedback_summary(
    db: AsyncSession, user_id: uuid.UUID
) -> tuple[float | None, list[str]]:
    """Aggregate-only view of the feedback a user has *received*, for
    llm_match_service's ranking prompt — never the individual rows, and
    never `comment` (free text has no business leaving this table; only the
    structured rating/tags do). Returns (average_rating, top_tag_keys),
    (None, []) if nobody has rated them yet. Capped to the 3 most frequent
    tags so the prompt stays short regardless of how many ratings pile up."""
    stmt = select(BlindChatFeedback.rating, BlindChatFeedback.tags).where(
        BlindChatFeedback.rated_user_id == user_id
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return None, []

    avg_rating = sum(r.rating for r in rows) / len(rows)
    tag_counts: dict[str, int] = {}
    for r in rows:
        for tag in r.tags.split(","):
            if tag and tag != "other":
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts, key=lambda t: tag_counts[t], reverse=True)[:3]
    return round(avg_rating, 1), top_tags
