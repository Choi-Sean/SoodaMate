from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.discovery import CandidateOut
from app.schemas.profile import PhotoOut
from app.services.discovery_service import get_candidates, get_photos_for_users, get_users_who_liked_me

router = APIRouter(prefix="/discovery", tags=["discovery"])


def _age(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _comma_list(value: str | None) -> list[str]:
    return [v for v in (value or "").split(",") if v]


async def _to_candidates_out(
    db: AsyncSession, results: list[tuple[Profile, float | None, bool]]
) -> list[CandidateOut]:
    photos_by_user = await get_photos_for_users(db, [p.user_id for p, _, _ in results])
    return [
        CandidateOut(
            user_id=profile.user_id,
            display_name=profile.display_name,
            age=_age(profile.birth_date),
            gender=profile.gender,
            bio=profile.bio,
            photos=[PhotoOut.model_validate(p) for p in photos_by_user.get(profile.user_id, [])],
            distance_km=distance_km,
            superliked_me=superliked_me,
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
            verified_badge=profile.verified_badge,
        )
        for profile, distance_km, superliked_me in results
    ]


async def _require_complete_profile(db: AsyncSession, user: User) -> Profile:
    viewer_profile = await db.get(Profile, user.id)
    if viewer_profile is None or not viewer_profile.is_profile_complete:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile before browsing")
    return viewer_profile


@router.get("/candidates", response_model=list[CandidateOut])
async def candidates(
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CandidateOut]:
    viewer_profile = await _require_complete_profile(db, user)
    results = await get_candidates(db, user, viewer_profile, limit=limit)
    return await _to_candidates_out(db, results)


@router.get("/liked-me", response_model=list[CandidateOut])
async def liked_me(
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CandidateOut]:
    viewer_profile = await _require_complete_profile(db, user)
    results = await get_users_who_liked_me(db, user, viewer_profile, limit=limit)
    return await _to_candidates_out(db, results)
