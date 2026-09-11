import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interaction import Block, Match
from app.models.blind_chat import BlindChatQueueEntry
from app.models.profile import Profile
from app.models.user import User
from app.schemas.match import BlindChatLimitOut, BlindChatQueueStatusOut
from app.services import push_service
from app.utils.premium import is_premium
from app.ws.connection_manager import manager

# Free members get this many blind-chat matches per calendar day (counted
# from Match rows, same "count real rows in a window" approach as
# match_service.SWIPE_LIMIT — a full-day window has plenty of margin against
# the sandbox/DB clock skew that ruled out short time-window checks
# elsewhere in this feature, see BlindChatQueueEntry.matched_id's docstring).
# Premium members and Unlimited Matching purchasers skip this entirely.
BLIND_CHAT_FREE_DAILY_LIMIT = 3


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

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
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
    remaining = max(0, BLIND_CHAT_FREE_DAILY_LIMIT - (count or 0))
    resets_at = None
    if remaining == 0:
        resets_at = today_start + timedelta(days=1)
    return BlindChatLimitOut(remaining=remaining, limit=BLIND_CHAT_FREE_DAILY_LIMIT, resets_at=resets_at)


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
    per-session overrides (see BlindChatQueueRequest), narrowing (never
    widening) their own profile-level defaults for this call only. The
    candidate side of every comparison below must instead read from
    BlindChatQueueEntry's own stored *_filter columns (falling back to the
    candidate's profile default via COALESCE when they didn't set one) —
    never straight from Profile — because the candidate already committed
    their own session's preferences to that row when *they* joined, and this
    viewer's search is what finds and matches against it later. Reading the
    candidate's live Profile columns instead would silently ignore whatever
    override the candidate's own session actually asked for."""
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
        ~User.is_banned,
        User.is_active,
        _csv_contains_any(BlindChatQueueEntry.categories, categories),
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
    plus bonuses for age and distance proximity."""
    score = len(shared_categories) * 1.0
    score += len(_shared_tags(viewer_profile.k_content_tags, candidate_profile.k_content_tags)) * 2.0
    score += len(_shared_tags(viewer_profile.interests, candidate_profile.interests)) * 2.0
    score += len(_shared_tags(viewer_profile.languages, candidate_profile.languages)) * 1.5
    if viewer_profile.open_to_language_exchange and candidate_profile.open_to_language_exchange:
        score += 1.0

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
    db: AsyncSession, user: User, viewer_profile: Profile, categories: list[str]
) -> tuple[BlindChatQueueEntry, Profile] | None:
    """Consumes 1 ai_match_credit (checked by the router before calling this)
    to instantly pair with the *best-scoring* currently-waiting candidate,
    rather than the live queue's plain FIFO order — see
    _compatibility_score. Deliberately scoped to the existing waiting pool
    (not every eligible user in the app) so both sides have already opted
    into blind chat; nobody is pulled into a match they never asked for."""
    filters = _compatibility_filters(user.id, viewer_profile, categories, None, None, None)
    filters += _distance_filters(viewer_profile, None)
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

    best = max(rows, key=score_row)
    return best[0], best[1]


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
    db: AsyncSession, user: User, viewer_profile: Profile, categories: list[str]
) -> Match | None:
    """Router-facing entry point: consumes 1 ai_match_credit and returns the
    freshly created Match, or returns None (credit left untouched — see
    schemas.match.AiMatchOut) if nobody compatible is currently waiting.
    Deliberately does NOT check the daily free-match limit — a purchased
    credit already implies "I've hit or don't care about the free cap.\""""
    if viewer_profile.ai_match_credits <= 0:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "no AI match credits left")

    found = await find_ai_match(db, user, viewer_profile, categories)
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
