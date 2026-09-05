from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Photo, Profile
from app.models.user import User
from app.schemas.profile import (
    IncognitoUpdate,
    PhotoConfirmRequest,
    PhotoOut,
    ProfileOut,
    ProfileUpdate,
    TravelModeRequest,
)

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

    if profile is None:
        profile = Profile(user_id=user.id, **body.model_dump(), is_profile_complete=is_complete)
        db.add(profile)
    else:
        for field, value in body.model_dump().items():
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
    existing = await db.scalar(
        select(Photo).where(Photo.user_id == user.id, Photo.position == body.position)
    )
    if existing is not None:
        existing.gcs_object_path = body.gcs_object_path
        photo = existing
    else:
        photo = Photo(user_id=user.id, gcs_object_path=body.gcs_object_path, position=body.position)
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
    return await _load_profile_out(db, user.id)
