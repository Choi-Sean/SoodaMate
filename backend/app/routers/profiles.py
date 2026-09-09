import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Photo, Profile
from app.models.user import User
from app.schemas.profile import (
    AgeFilterUpdate,
    BasicFilterUpdate,
    IncognitoUpdate,
    PhotoConfirmRequest,
    PhotoOut,
    PhotoReorderRequest,
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
    profile_data["k_content_tags"] = ",".join(body.k_content_tags) if body.k_content_tags else None

    if profile is None:
        profile = Profile(user_id=user.id, **profile_data, is_profile_complete=is_complete)
        db.add(profile)
    else:
        # display_name/legal_first_name/birth_date/gender are all locked
        # after initial profile creation — a name, age, or gender that keeps
        # changing makes a user harder to recognize/report, and
        # legal_first_name/birth_date feed identity checks elsewhere.
        # Mobile makes all four fields read-only for this reason — this is
        # the backend enforcing the same rule for direct API calls. A real
        # change request goes through support@soodamate.com (photo ID
        # required, reviewed by hand), not this endpoint.
        profile_data["display_name"] = profile.display_name
        profile_data["legal_first_name"] = profile.legal_first_name
        profile_data["birth_date"] = profile.birth_date
        profile_data["gender"] = profile.gender
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


@router.put("/me/photos/reorder", response_model=list[PhotoOut])
async def reorder_photos(
    body: PhotoReorderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PhotoOut]:
    photos = (
        await db.execute(select(Photo).where(Photo.user_id == user.id))
    ).scalars().all()
    by_id = {p.id: p for p in photos}
    if set(body.photo_ids) != set(by_id.keys()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "photo_ids must list every photo exactly once")

    # UNIQUE(UserId, Position) means writing final positions directly can
    # collide mid-transaction (e.g. swapping 0<->1 tries to put photo B at
    # position 0 while photo A -- not yet moved off it -- is still there).
    # Push everything to negative placeholders first, then assign the real,
    # already-conflict-free positions.
    for i, photo in enumerate(by_id.values()):
        photo.position = -(i + 1)
    await db.flush()
    for index, photo_id in enumerate(body.photo_ids):
        by_id[photo_id].position = index
    await db.commit()

    reordered = (
        await db.execute(select(Photo).where(Photo.user_id == user.id).order_by(Photo.position))
    ).scalars().all()
    return [PhotoOut.model_validate(p) for p in reordered]


@router.delete("/me/photos/{photo_id}", status_code=204)
async def delete_photo(
    photo_id,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    photo = await db.get(Photo, photo_id)
    if photo is None or photo.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "photo not found")
    remaining = await db.scalar(select(func.count()).select_from(Photo).where(Photo.user_id == user.id))
    if remaining <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "at least one photo is required")
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
    profile.religion_filter = ",".join(body.religion_filter) if body.religion_filter else None

    # Everything else lives in one JSON blob (Profile.premium_filters_json —
    # see that column's comment). Full-replace semantics, same as
    # religion_filter above: the client always sends its whole current
    # filter selection, and an empty list here clears that one dimension
    # (omitted from the stored JSON) rather than leaving a stale value
    # behind.
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
    profile.premium_filters_json = json.dumps(extra) if extra else None

    await db.commit()
    await db.refresh(profile)
    return await _load_profile_out(db, user.id)


@router.put("/me/basic-filters", response_model=ProfileOut)
async def set_basic_filters(
    body: BasicFilterUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfileOut:
    """Free for everyone, unlike set_premium_filters above — every field
    here (distance, race/ethnicity, height, languages, interests, verified-
    only, language-exchange-only, and the two "if I run out" expansion
    toggles) is part of the Basic filters tab, not Advanced."""
    profile = await db.get(Profile, user.id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")

    profile.max_distance_km = body.max_distance_km
    profile.race_filter = ",".join(body.race_filter) if body.race_filter else None
    profile.height_filter_min = body.height_min
    profile.height_filter_max = body.height_max
    profile.languages_filter = ",".join(body.languages_filter) if body.languages_filter else None
    profile.interests_filter = ",".join(body.interests_filter) if body.interests_filter else None
    profile.k_content_filter = ",".join(body.k_content_filter) if body.k_content_filter else None
    profile.verified_only = body.verified_only
    profile.language_exchange_only = body.language_exchange_only
    profile.expand_distance_if_low = body.expand_distance_if_low
    profile.expand_others_if_low = body.expand_others_if_low

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
