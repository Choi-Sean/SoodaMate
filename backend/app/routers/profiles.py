import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Photo, Profile
from app.models.user import User
from app.schemas.profile import (
    AgeFilterUpdate,
    IncognitoUpdate,
    PhotoConfirmRequest,
    PhotoOut,
    PremiumFilterUpdate,
    ProfileOut,
    ProfileUpdate,
    TravelModeRequest,
)
from app.services import storage_service
from app.services.payment_service import is_premium_member

router = APIRouter(prefix="/profiles", tags=["profiles"])


async def _load_profile_out(db: AsyncSession, user_id) -> ProfileOut:
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "profile not found")
    photos = (
        await db.execute(select(Photo).where(Photo.user_id == user_id).order_by(Photo.position))
    ).scalars().all()
    out = ProfileOut.model_validate(profile)
    out.photos = [PhotoOut.model_validate(p) for p in photos]
    return out


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ProfileOut:
    return await _load_profile_out(db, user.id)


@router.put("/me", response_model=ProfileOut)
async def update_my_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    profile = await db.get(Profile, user.id)
    photo_count = await db.scalar(select(Photo).where(Photo.user_id == user.id).limit(1))
    is_complete = photo_count is not None

    # interests/languages are lists on the wire but a single comma-separated
    # column in the DB (same convention as race_filter/religion_filter).
    profile_data = body.model_dump()
    profile_data["interests"] = ",".join(body.interests) if body.interests else None
    profile_data["languages"] = ",".join(body.languages) if body.languages else None

    if profile is None:
        profile = Profile(user_id=user.id, **profile_data, is_profile_complete=is_complete)
        db.add(profile)
    else:
        for field, value in profile_data.items():
            setattr(profile, field, value)
        profile.is_profile_complete = is_complete

    await db.commit()
    # onupdate=func.now() (and, for a fresh row, server_default) leaves
    # updated_at server-computed and unloaded after commit; refresh so the
    # response model doesn't trigger a lazy load outside of an await.
    await db.refresh(profile)
    return await _load_profile_out(db, user.id)


@router.post("/me/photos/confirm", response_model=PhotoOut, status_code=201)
async def confirm_photo(
    body: PhotoConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PhotoOut:
    media_type = storage_service.media_type_from_object_path(body.gcs_object_path)

    existing = await db.scalar(
        select(Photo).where(Photo.user_id == user.id, Photo.position == body.position)
    )
    if existing is not None:
        existing.gcs_object_path = body.gcs_object_path
        existing.media_type = media_type
        photo = existing
    else:
        photo = Photo(
            user_id=user.id, gcs_object_path=body.gcs_object_path, position=body.position, media_type=media_type
        )
        db.add(photo)

    profile = await db.get(Profile, user.id)
    if profile is not None:
        profile.is_profile_complete = True

    await db.commit()
    await db.refresh(photo)
    return PhotoOut.model_validate(photo)


@router.delete("/me/photos/{photo_id}", status_code=204)
async def delete_photo(
    photo_id,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    photo = await db.get(Photo, photo_id)
    if photo is None or photo.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "photo not found")
    await db.delete(photo)
    await db.commit()


@router.post("/me/incognito", response_model=ProfileOut)
async def set_incognito(
    body: IncognitoUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    profile = await db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    profile.is_incognito = body.is_incognito
    await db.commit()
    # updated_at is server-computed (onupdate=func.now()) and left unloaded
    # after commit — refresh so ProfileOut's response model doesn't trigger
    # a lazy load outside of an await (see update_my_profile's same fix).
    await db.refresh(profile)
    return await _load_profile_out(db, user.id)


@router.put("/me/premium-filters", response_model=ProfileOut)
async def set_premium_filters(
    body: PremiumFilterUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    profile = await db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    if not is_premium_member(profile):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "an active premium membership is required to filter by these fields",
        )
    profile.race_filter = ",".join(body.race_filter) if body.race_filter else None
    profile.religion_filter = ",".join(body.religion_filter) if body.religion_filter else None

    # Everything else lives in one JSON blob (Profile.premium_filters_json —
    # see that column's comment). Full-replace semantics, same as
    # race_filter/religion_filter above: the client always sends its whole
    # current filter selection, and an empty list/null bound here clears
    # that one dimension (omitted from the stored JSON) rather than leaving
    # a stale value behind.
    extra = {
        "political_view_filter": body.political_view_filter,
        "exercise_frequency_filter": body.exercise_frequency_filter,
        "smoking_filter": body.smoking_filter,
        "cannabis_filter": body.cannabis_filter,
        "relationship_goal_filter": body.relationship_goal_filter,
        "wants_kids_filter": body.wants_kids_filter,
        "has_kids_filter": body.has_kids_filter,
    }
    extra = {k: v for k, v in extra.items() if v}
    if body.height_min is not None:
        extra["height_min"] = body.height_min
    if body.height_max is not None:
        extra["height_max"] = body.height_max
    profile.premium_filters_json = json.dumps(extra) if extra else None

    await db.commit()
    await db.refresh(profile)
    return await _load_profile_out(db, user.id)


@router.put("/me/age-filter", response_model=ProfileOut)
async def set_age_filter(
    body: AgeFilterUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    """Free for everyone, unlike set_premium_filters above — age range has
    always been an unpaywalled part of discovery (discovery_service.py
    applies min_age_pref/max_age_pref unconditionally)."""
    profile = await db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    profile.min_age_pref = body.min_age_pref
    profile.max_age_pref = body.max_age_pref
    await db.commit()
    await db.refresh(profile)
    return await _load_profile_out(db, user.id)


@router.post("/me/travel", response_model=ProfileOut)
async def set_travel_mode(
    body: TravelModeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    profile = await db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    profile.travel_lat = body.lat
    profile.travel_lng = body.lng
    profile.travel_expires_at = datetime.now(timezone.utc) + timedelta(hours=body.duration_hours)
    await db.commit()
    await db.refresh(profile)
    return await _load_profile_out(db, user.id)


@router.delete("/me/travel", response_model=ProfileOut)
async def clear_travel_mode(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ProfileOut:
    profile = await db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    profile.travel_lat = None
    profile.travel_lng = None
    profile.travel_expires_at = None
    await db.commit()
    await db.refresh(profile)
    return await _load_profile_out(db, user.id)
