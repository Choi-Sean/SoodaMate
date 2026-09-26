import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Photo, Profile

# Server-side mirror of mobile/src/utils/profileCompleteness.ts's 18-point
# "profile strength" checklist — kept in sync with that file's check list by
# hand. Distinct from the much weaker Profile.is_profile_complete column
# (just photo + display_name + birth_date + gender, enough to finish
# ProfileSetup but not enough to be worth matching on): this is the "70%
# filled in" bar already used to gate Blind Chat, extended to also gate
# Discover/Swipe (see routers/discovery.py, services/match_service.py).
MIN_COMPLETENESS_FOR_ACTIVE = 70
_CHECK_COUNT = 18


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def calculate_completeness_percent(profile: Profile, photo_count: int, has_video: bool) -> int:
    checks = [
        _has_text(profile.bio),
        photo_count >= 3,
        has_video,
        profile.race_ethnicity is not None,
        profile.religion is not None,
        profile.political_view is not None,
        profile.height_cm is not None,
        _has_text(profile.occupation),
        _has_text(profile.education),
        _has_text(profile.hometown),
        profile.smoking is not None,
        profile.exercise_frequency is not None,
        profile.relationship_goal is not None,
        profile.wants_kids is not None,
        profile.has_kids is not None,
        _has_text(profile.interests),
        _has_text(profile.languages),
        profile.face_verified,
    ]
    assert len(checks) == _CHECK_COUNT  # keep in sync with the JS checklist's length
    filled = sum(1 for c in checks if c)
    return round(filled / len(checks) * 100)


def is_richly_complete(profile: Profile, photo_count: int, has_video: bool) -> bool:
    return calculate_completeness_percent(profile, photo_count, has_video) >= MIN_COMPLETENESS_FOR_ACTIVE


async def load_richness(db: AsyncSession, user_id: uuid.UUID, profile: Profile) -> bool:
    """Single-profile version — used where only one person's richness needs
    checking (the viewer trying to browse/swipe), not a whole candidate pool
    (see richness_sql_filter for that)."""
    rows = (await db.execute(select(Photo.media_type).where(Photo.user_id == user_id))).scalars().all()
    return is_richly_complete(profile, photo_count=len(rows), has_video="video" in rows)


# Minimum summed-check count for MIN_COMPLETENESS_FOR_ACTIVE% of _CHECK_COUNT
# checks — round() here matches calculate_completeness_percent's own
# round(filled/total*100) >= MIN_COMPLETENESS_FOR_ACTIVE comparison exactly
# (verified: 12/18 -> 67% fails, 13/18 -> 72% passes).
_MIN_CHECKS_FILLED = round(_CHECK_COUNT * MIN_COMPLETENESS_FOR_ACTIVE / 100)


def richness_sql_filter():
    """SQL-expression version of is_richly_complete, for filtering a whole
    candidate pool as a plain WHERE condition (see discovery_service.py) —
    composes cleanly with the existing pool-overfetch/backfill logic there,
    unlike a post-fetch Python filter which would silently shrink results
    below the requested page size."""
    photo_count = (
        select(func.count(Photo.id)).where(Photo.user_id == Profile.user_id).correlate(Profile).scalar_subquery()
    )
    has_video = (
        select(func.count(Photo.id))
        .where(Photo.user_id == Profile.user_id, Photo.media_type == "video")
        .correlate(Profile)
        .scalar_subquery()
    )

    def _text(col):
        return func.length(func.coalesce(col, "")) > 0

    conditions = [
        _text(Profile.bio),
        photo_count >= 3,
        has_video > 0,
        Profile.race_ethnicity.isnot(None),
        Profile.religion.isnot(None),
        Profile.political_view.isnot(None),
        Profile.height_cm.isnot(None),
        _text(Profile.occupation),
        _text(Profile.education),
        _text(Profile.hometown),
        Profile.smoking.isnot(None),
        Profile.exercise_frequency.isnot(None),
        Profile.relationship_goal.isnot(None),
        Profile.wants_kids.isnot(None),
        Profile.has_kids.isnot(None),
        _text(Profile.interests),
        _text(Profile.languages),
        # Unlike a bare boolean column in a top-level WHERE list (which
        # SQLAlchemy's MSSQL dialect compiles to `= 1` portably, see the
        # is_profile_complete convention elsewhere), a bare column used as a
        # CASE WHEN condition is NOT treated as boolean by T-SQL ("An
        # expression of non-boolean type specified in a context where a
        # condition is expected") — needs an explicit comparison here.
        Profile.face_verified == True,  # noqa: E712
    ]
    assert len(conditions) == _CHECK_COUNT  # keep in sync with calculate_completeness_percent above
    score = sum(case((c, 1), else_=0) for c in conditions)
    return score >= _MIN_CHECKS_FILLED
