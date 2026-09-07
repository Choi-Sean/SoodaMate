import json
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database import engine
from app.models.interaction import Block, Match, Swipe
from app.models.profile import Photo, Profile
from app.models.user import User
from app.services.payment_service import is_premium_member

# MSSQL has no RANDOM() (T-SQL's idiom is ORDER BY NEWID()) — resolved once
# from the live engine's dialect rather than per-request.
_ORDER_RANDOM = func.newid() if engine.dialect.name == "mssql" else func.random()

# Profile column each premium_filters_json list-key restricts on.
_LIST_FILTER_COLUMNS = {
    "political_view_filter": Profile.political_view,
    "exercise_frequency_filter": Profile.exercise_frequency,
    "smoking_filter": Profile.smoking,
    "cannabis_filter": Profile.cannabis,
    "relationship_goal_filter": Profile.relationship_goal,
    "wants_kids_filter": Profile.wants_kids,
    "has_kids_filter": Profile.has_kids,
}


def _extra_premium_filters(viewer_profile: Profile) -> list:
    """The premium_filters_json-backed dimensions (everything beyond
    religion_filter, which has its own column and is handled inline in
    get_candidates) — see schemas/profile.py's PremiumFilters for the typed
    shape this mirrors. height used to live in this JSON blob too; it's a
    free Basic-tab filter now with its own columns (see
    _basic_filters below), not part of the premium set at all."""
    if not viewer_profile.premium_filters_json:
        return []
    try:
        stored = json.loads(viewer_profile.premium_filters_json)
    except (ValueError, TypeError):
        return []

    filters = []
    for key, column in _LIST_FILTER_COLUMNS.items():
        values = stored.get(key)
        if values:
            filters.append(column.in_(values))
    return filters


def _csv_contains_any(column, values: list[str]):
    """Portable "does this comma-separated column contain any of these
    exact values" match (languages/interests are stored the same
    comma-joined way as race_filter, but as a multi-value column instead of
    a single value, so a plain .in_() doesn't apply). Wraps the column in
    leading/trailing commas so a LIKE '%,val,%' match can never hit a
    partial word (e.g. "art" inside "cart") regardless of val's position."""
    wrapped = func.concat(",", column, ",")
    return or_(*[wrapped.like(f"%,{v},%") for v in values])


def _basic_filters(viewer_profile: Profile) -> list:
    """Every free (Basic-tab) filter dimension beyond age/gender/distance,
    which get_candidates already applies inline — race/ethnicity, height,
    languages, interests, and verified-only. None of this requires
    is_premium_member; see routers/profiles.py::set_basic_filters."""
    filters = []
    if viewer_profile.race_filter:
        filters.append(Profile.race_ethnicity.in_(viewer_profile.race_filter.split(",")))
    if viewer_profile.height_filter_min is not None:
        filters.append(Profile.height_cm >= viewer_profile.height_filter_min)
    if viewer_profile.height_filter_max is not None:
        filters.append(Profile.height_cm <= viewer_profile.height_filter_max)
    if viewer_profile.languages_filter:
        filters.append(_csv_contains_any(Profile.languages, viewer_profile.languages_filter.split(",")))
    if viewer_profile.interests_filter:
        filters.append(_csv_contains_any(Profile.interests, viewer_profile.interests_filter.split(",")))
    if viewer_profile.verified_only:
        filters.append(Profile.face_verified)
    return filters


def _age_to_birth_date_bounds(min_age: int, max_age: int) -> tuple[date, date]:
    today = date.today()
    # Born on/before this date => at least min_age today.
    max_birth_date = today.replace(year=today.year - min_age)
    # Born on/after this date => at most max_age today.
    min_birth_date = today.replace(year=today.year - max_age - 1) + timedelta(days=1)
    return min_birth_date, max_birth_date


def _haversine_km(lat1, lng1, lat2, lng2):
    r = 6371.0
    lat1r, lat2r = func.radians(lat1), func.radians(lat2)
    dlat = func.radians(lat2 - lat1)
    dlng = func.radians(lng2 - lng1)
    # func.power (not func.pow) — POWER is the T-SQL name; Postgres accepts
    # it too, so this is portable both ways.
    a = func.power(func.sin(dlat / 2), 2) + func.cos(lat1r) * func.cos(lat2r) * func.power(
        func.sin(dlng / 2), 2
    )
    return r * 2 * func.asin(func.sqrt(a))


def _effective_location(profile: Profile) -> tuple[float | None, float | None]:
    """Phase 18 travel mode: an active (non-expired) travel override replaces
    the profile's real location for discovery purposes, for both directions
    of the distance calc — so a traveling user is genuinely repositioned
    into their destination's pool for others too, not just a client-side
    view override."""
    if profile.travel_lat is not None and profile.travel_lng is not None and profile.travel_expires_at is not None:
        expires = profile.travel_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires > datetime.now(timezone.utc):
            return profile.travel_lat, profile.travel_lng
    return profile.location_lat, profile.location_lng


def _core_exclusions(viewer: User, viewer_profile: Profile) -> list:
    """The non-negotiable conditions that apply no matter what — even the
    broadest "show anyone" fallback in get_candidates still respects
    these: never yourself, never an incomplete/banned/inactive/incognito
    profile, never someone already swiped on or blocked either direction,
    and never a gender mismatch (that one's not really "negotiable" for a
    dating app's fallback either)."""
    already_swiped = exists().where(
        and_(Swipe.from_user_id == viewer.id, Swipe.to_user_id == Profile.user_id)
    )
    blocked_either_direction = exists().where(
        or_(
            and_(Block.blocker_id == viewer.id, Block.blocked_id == Profile.user_id),
            and_(Block.blocker_id == Profile.user_id, Block.blocked_id == viewer.id),
        )
    )
    gender_filters = [Profile.gender == viewer_profile.interested_in] if viewer_profile.interested_in != "all" else []
    mutual_interest = or_(Profile.interested_in == "all", Profile.interested_in == viewer_profile.gender)

    return [
        Profile.user_id != viewer.id,
        # Plain column truthiness (not .is_(True)/.is_(False)) — MSSQL has
        # no IS TRUE/IS FALSE syntax (only IS NULL), so this compiles
        # portably to `= 1` / `= 0` there instead of erroring.
        Profile.is_profile_complete,
        ~Profile.is_incognito,  # Phase 18 — hidden from fresh Discover browsing
        ~User.is_banned,
        User.is_active,
        mutual_interest,
        *gender_filters,
        ~already_swiped,
        ~blocked_either_direction,
    ]


async def _query_pool(db: AsyncSession, viewer: User, where: list, pool_size: int) -> list[tuple[Profile, bool]]:
    """One SELECT against the given WHERE clauses, ranked the same way
    every candidate pool in this app is (superliked-me first, then
    boosted, then recently-active, then random) — returns
    (profile, is_superliker) pairs, most-preferred first."""
    superliked_me_exists = exists().where(
        and_(
            Swipe.from_user_id == Profile.user_id,
            Swipe.to_user_id == viewer.id,
            Swipe.action == "superlike",
        )
    )
    boosted_expr = and_(Profile.boost_active_until.isnot(None), Profile.boost_active_until > func.now())
    superliked_me = case((superliked_me_exists, 1), else_=0)
    boosted = case((boosted_expr, 1), else_=0)

    stmt = (
        select(Profile, superliked_me.label("superliked_me"))
        .join(User, User.id == Profile.user_id)
        .where(*where)
        .order_by(
            superliked_me.label("superliked_me").desc(),
            boosted.label("boosted").desc(),
            User.last_active_at.desc(),
            _ORDER_RANDOM,
        )
        .limit(pool_size)
    )
    rows = (await db.execute(stmt)).all()
    return [(profile, bool(is_superliker)) for profile, is_superliker in rows]


async def _with_distance(
    db: AsyncSession, viewer_profile: Profile, pool: list[tuple[Profile, bool]]
) -> list[tuple[Profile, float | None, bool]]:
    viewer_lat, viewer_lng = _effective_location(viewer_profile)
    out: list[tuple[Profile, float | None, bool]] = []
    for profile, is_superliker in pool:
        distance_km = None
        candidate_lat, candidate_lng = _effective_location(profile)
        if viewer_lat is not None and viewer_lng is not None and candidate_lat is not None and candidate_lng is not None:
            d = await db.scalar(select(_haversine_km(viewer_lat, viewer_lng, candidate_lat, candidate_lng)))
            distance_km = float(d) if d is not None else None
        out.append((profile, distance_km, is_superliker))
    return out


# Multiplier over `limit` for stage-1's pool fetch — distance filtering
# happens in Python after the fact (see _with_distance), so the SQL fetch
# needs headroom beyond `limit` or a run of too-far candidates could starve
# the final result below `limit` even though closer ones exist further
# down the ranking.
_POOL_MULTIPLIER = 4


async def get_candidates(
    db: AsyncSession, viewer: User, viewer_profile: Profile, limit: int = 20
) -> list[tuple[Profile, float | None, bool]]:
    """Returns (candidate_profile, distance_km_or_None, superliked_me)
    tuples, ranked superliked-me first, then boosted, then randomized.

    Three stages, each only run if the previous one came up short:
      1. Strict: age + every Basic filter (race/height/languages/
         interests/verified-only) + Advanced filters (premium only) +
         distance within max_distance_km.
      2. If still short and expand_distance_if_low: same filters, but
         candidates beyond max_distance_km are allowed too (closest first).
      3. If still short and expand_others_if_low: every optional filter
         above is dropped entirely (age/Basic/Advanced/distance) - anyone
         who isn't excluded by the non-negotiable core conditions
         (yourself, incomplete/banned/blocked/already-swiped/gender
         mismatch) backfills the remaining slots.
    Stage 2/3 results are appended after stage 1's, so the UI can still
    reflect "these matched your filters, these didn't" via distance/
    profile fields even though the API itself doesn't label the stage.
    """
    core_where = _core_exclusions(viewer, viewer_profile)

    min_birth, max_birth = _age_to_birth_date_bounds(viewer_profile.min_age_pref, viewer_profile.max_age_pref)
    age_where = [Profile.birth_date >= min_birth, Profile.birth_date <= max_birth]

    basic_where = _basic_filters(viewer_profile)

    # Advanced (premium_filters_json + religion_filter) still requires an
    # active membership to apply at all — a lapsed membership can't keep
    # benefiting from filters configured while it was active, checked here
    # at read time rather than only when the filter was set.
    advanced_where = []
    if is_premium_member(viewer_profile):
        if viewer_profile.religion_filter:
            advanced_where.append(Profile.religion.in_(viewer_profile.religion_filter.split(",")))
        advanced_where.extend(_extra_premium_filters(viewer_profile))

    pool_size = limit * _POOL_MULTIPLIER

    # --- Stage 1: strict ---
    strict_pool = await _query_pool(db, viewer, [*core_where, *age_where, *basic_where, *advanced_where], pool_size)
    strict_with_dist = await _with_distance(db, viewer_profile, strict_pool)

    within_cap = [r for r in strict_with_dist if r[1] is None or r[1] <= viewer_profile.max_distance_km]
    beyond_cap = sorted(
        (r for r in strict_with_dist if r[1] is not None and r[1] > viewer_profile.max_distance_km),
        key=lambda r: r[1],
    )

    results: list[tuple[Profile, float | None, bool]] = within_cap[:limit]
    seen_ids = {p.user_id for p, _, _ in results}

    # --- Stage 2: relax the distance cap ---
    if len(results) < limit and viewer_profile.expand_distance_if_low:
        for r in beyond_cap:
            if len(results) >= limit:
                break
            if r[0].user_id not in seen_ids:
                results.append(r)
                seen_ids.add(r[0].user_id)

    # --- Stage 3: drop age + every Basic filter, backfill with anyone else
    # who still passes Advanced (premium_filters_json + religion_filter) ---
    # this only ever relaxes the free tier's own filters; a paying member's
    # Advanced selections stay enforced even in the broadest fallback, or
    # paying for them would buy nothing.
    if len(results) < limit and viewer_profile.expand_others_if_low:
        fallback_pool = await _query_pool(db, viewer, [*core_where, *advanced_where], pool_size)
        fallback_pool = [(p, s) for p, s in fallback_pool if p.user_id not in seen_ids]
        fallback_with_dist = await _with_distance(db, viewer_profile, fallback_pool)
        for r in fallback_with_dist:
            if len(results) >= limit:
                break
            if r[0].user_id not in seen_ids:
                results.append(r)
                seen_ids.add(r[0].user_id)

    return results


async def get_users_who_liked_me(
    db: AsyncSession, viewer: User, viewer_profile: Profile, limit: int = 50
) -> list[tuple[Profile, float | None, bool]]:
    """People who liked/superliked the viewer, most recent first — excludes
    anyone the viewer already responded to either way (a like would already
    be a Match; a pass means the viewer already rejected them) and anyone
    blocked either direction. Returns the same (profile, distance_km,
    is_superlike) shape as get_candidates so routers/discovery.py can build
    CandidateOut the exact same way for both."""
    their_like = aliased(Swipe)
    my_response = aliased(Swipe)

    already_responded = exists().where(
        and_(my_response.from_user_id == viewer.id, my_response.to_user_id == their_like.from_user_id)
    )
    already_matched = exists().where(
        or_(
            and_(Match.user_a_id == viewer.id, Match.user_b_id == their_like.from_user_id),
            and_(Match.user_a_id == their_like.from_user_id, Match.user_b_id == viewer.id),
        )
    )
    blocked_either_direction = exists().where(
        or_(
            and_(Block.blocker_id == viewer.id, Block.blocked_id == their_like.from_user_id),
            and_(Block.blocker_id == their_like.from_user_id, Block.blocked_id == viewer.id),
        )
    )

    stmt = (
        select(Profile, their_like.action)
        .join(Profile, Profile.user_id == their_like.from_user_id)
        .join(User, User.id == Profile.user_id)
        .where(
            their_like.to_user_id == viewer.id,
            their_like.action.in_(["like", "superlike"]),
            Profile.is_profile_complete,
            ~User.is_banned,
            User.is_active,
            ~already_responded,
            ~already_matched,
            ~blocked_either_direction,
        )
        .order_by(their_like.created_at.desc())
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()

    viewer_lat, viewer_lng = _effective_location(viewer_profile)
    results: list[tuple[Profile, float | None, bool]] = []
    for profile, action in rows:
        distance_km = None
        candidate_lat, candidate_lng = _effective_location(profile)
        if viewer_lat is not None and viewer_lng is not None and candidate_lat is not None and candidate_lng is not None:
            d = await db.scalar(select(_haversine_km(viewer_lat, viewer_lng, candidate_lat, candidate_lng)))
            distance_km = float(d) if d is not None else None
        results.append((profile, distance_km, action == "superlike"))

    return results


async def get_photos_for_users(db: AsyncSession, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[Photo]]:
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(Photo).where(Photo.user_id.in_(user_ids)).order_by(Photo.user_id, Photo.position)
        )
    ).scalars()
    out: dict[uuid.UUID, list[Photo]] = {uid: [] for uid in user_ids}
    for photo in rows:
        out.setdefault(photo.user_id, []).append(photo)
    return out
