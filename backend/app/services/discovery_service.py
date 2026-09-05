import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.models.interaction import Block, Swipe
from app.models.profile import Photo, Profile
from app.models.user import User

# MSSQL has no RANDOM() (T-SQL's idiom is ORDER BY NEWID()) — resolved once
# from the live engine's dialect rather than per-request.
_ORDER_RANDOM = func.newid() if engine.dialect.name == "mssql" else func.random()


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


async def get_candidates(
    db: AsyncSession, viewer: User, viewer_profile: Profile, limit: int = 20
) -> list[tuple[Profile, float | None, bool]]:
    """Returns (candidate_profile, distance_km_or_None, superliked_me) tuples,
    ranked superliked-me first, then boosted, then randomized."""
    min_birth, max_birth = _age_to_birth_date_bounds(
        viewer_profile.min_age_pref, viewer_profile.max_age_pref
    )

    already_swiped = exists().where(
        and_(Swipe.from_user_id == viewer.id, Swipe.to_user_id == Profile.user_id)
    )
    blocked_either_direction = exists().where(
        or_(
            and_(Block.blocker_id == viewer.id, Block.blocked_id == Profile.user_id),
            and_(Block.blocker_id == Profile.user_id, Block.blocked_id == viewer.id),
        )
    )
    superliked_me_exists = exists().where(
        and_(
            Swipe.from_user_id == Profile.user_id,
            Swipe.to_user_id == viewer.id,
            Swipe.action == "superlike",
        )
    )
    boosted_expr = and_(Profile.boost_active_until.isnot(None), Profile.boost_active_until > func.now())
    # MSSQL can't use EXISTS(...)/a boolean AND expression directly as a
    # SELECT or ORDER BY column (T-SQL only allows boolean predicates inside
    # WHERE/HAVING/ON/CASE) — CASE WHEN...THEN 1 ELSE 0 END is the portable
    # way to turn either into a 0/1 scalar both dialects can select/sort by.
    superliked_me = case((superliked_me_exists, 1), else_=0)
    boosted = case((boosted_expr, 1), else_=0)

    gender_filters = [Profile.gender == viewer_profile.interested_in] if viewer_profile.interested_in != "all" else []
    mutual_interest = or_(Profile.interested_in == "all", Profile.interested_in == viewer_profile.gender)

    # Profile has no ORM relationship to Photo, so photos are fetched with a
    # separate query in the router layer (see routers/discovery.py).
    stmt = (
        select(Profile, superliked_me.label("superliked_me"))
        .join(User, User.id == Profile.user_id)
        .where(
            Profile.user_id != viewer.id,
            # Plain column truthiness (not .is_(True)/.is_(False)) — MSSQL
            # has no IS TRUE/IS FALSE syntax (only IS NULL), so this compiles
            # portably to `= 1` / `= 0` there instead of erroring.
            Profile.is_profile_complete,
            ~Profile.is_incognito,  # Phase 18 — hidden from fresh Discover browsing
            ~User.is_banned,
            User.is_active,
            Profile.birth_date >= min_birth,
            Profile.birth_date <= max_birth,
            mutual_interest,
            *gender_filters,
            ~already_swiped,
            ~blocked_either_direction,
        )
        .order_by(
            superliked_me.label("superliked_me").desc(),
            boosted.label("boosted").desc(),
            User.last_active_at.desc(),
            _ORDER_RANDOM,
        )
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()

    viewer_lat, viewer_lng = _effective_location(viewer_profile)

    results: list[tuple[Profile, float | None, bool]] = []
    for profile, is_superliker in rows:
        distance_km = None
        candidate_lat, candidate_lng = _effective_location(profile)
        if viewer_lat is not None and viewer_lng is not None and candidate_lat is not None and candidate_lng is not None:
            d = await db.scalar(select(_haversine_km(viewer_lat, viewer_lng, candidate_lat, candidate_lng)))
            distance_km = float(d) if d is not None else None
            if distance_km is not None and distance_km > viewer_profile.max_distance_km:
                continue
        results.append((profile, distance_km, bool(is_superliker)))

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
