import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.config import settings


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gcs_object_path: str
    position: int

    @computed_field
    @property
    def url(self) -> str:
        # Bucket is public-read with non-guessable UUID paths (see
        # storage_service.py) — no signed GET URL needed for v1.
        return f"https://storage.googleapis.com/{settings.gcs_bucket_name}/{self.gcs_object_path}"


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)
    birth_date: date
    gender: str = Field(pattern="^(male|female|other)$")
    interested_in: str = Field(pattern="^(male|female|other|all)$")
    bio: str | None = Field(default=None, max_length=1000)
    location_lat: float | None = None
    location_lng: float | None = None
    min_age_pref: int = Field(default=18, ge=18, le=99)
    max_age_pref: int = Field(default=99, ge=18, le=99)
    max_distance_km: int = Field(default=50, ge=1, le=500)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    display_name: str
    birth_date: date
    gender: str
    interested_in: str
    bio: str | None
    location_lat: float | None
    location_lng: float | None
    min_age_pref: int
    max_age_pref: int
    max_distance_km: int
    is_profile_complete: bool
    verified_badge: str | None = None
    superlike_credits: int = 0
    boost_credits: int = 0
    boost_active_until: datetime | None = None
    is_incognito: bool = False
    travel_lat: float | None = None
    travel_lng: float | None = None
    travel_expires_at: datetime | None = None
    updated_at: datetime
    photos: list[PhotoOut] = []


class PresignRequest(BaseModel):
    content_type: str = Field(pattern="^image/(jpeg|png|webp)$")
    position: int = Field(ge=0, le=8)


class PresignResponse(BaseModel):
    upload_url: str
    gcs_object_path: str


class PhotoConfirmRequest(BaseModel):
    gcs_object_path: str
    position: int = Field(ge=0, le=8)


class IncognitoUpdate(BaseModel):
    is_incognito: bool


class TravelModeRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    duration_hours: int = Field(default=24, ge=1, le=24 * 30)
