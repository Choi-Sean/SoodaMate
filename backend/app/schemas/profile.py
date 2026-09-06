import json
import uuid
from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.services.storage_service import build_public_url


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    gcs_object_path: str
    position: int
    media_type: str

    @computed_field
    @property
    def url(self) -> str:
        return build_public_url(self.gcs_object_path)


class PremiumFilters(BaseModel):
    """The premium_filters_json-backed dimensions only — race_filter/
    religion_filter stay top-level ProfileOut fields as before (pre-existing,
    unchanged) rather than being folded in here, to avoid disturbing
    anything already reading them there."""

    political_view_filter: list[str] = []
    exercise_frequency_filter: list[str] = []
    smoking_filter: list[str] = []
    cannabis_filter: list[str] = []
    relationship_goal_filter: list[str] = []
    wants_kids_filter: list[str] = []
    has_kids_filter: list[str] = []
    height_min: int | None = None
    height_max: int | None = None


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)
    legal_first_name: str = Field(min_length=1, max_length=50)
    birth_date: date
    gender: str = Field(pattern="^(male|female|other)$")
    interested_in: str = Field(pattern="^(male|female|other|all)$")
    bio: str | None = Field(default=None, max_length=1000)
    location_lat: float | None = None
    location_lng: float | None = None
    min_age_pref: int = Field(default=18, ge=18, le=99)
    max_age_pref: int = Field(default=99, ge=18, le=99)
    max_distance_km: int = Field(default=50, ge=1, le=500)
    race_ethnicity: str | None = Field(default=None, max_length=50)
    religion: str | None = Field(default=None, max_length=50)
    political_view: str | None = Field(default=None, max_length=50)
    height_cm: int | None = Field(default=None, ge=50, le=272)
    occupation: str | None = Field(default=None, max_length=100)
    education: str | None = Field(default=None, max_length=100)
    hometown: str | None = Field(default=None, max_length=100)
    smoking: str | None = Field(default=None, max_length=30)
    cannabis: str | None = Field(default=None, max_length=30)
    exercise_frequency: str | None = Field(default=None, max_length=30)
    relationship_goal: str | None = Field(default=None, max_length=30)
    wants_kids: str | None = Field(default=None, max_length=30)
    has_kids: str | None = Field(default=None, max_length=30)
    interests: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    display_name: str
    legal_first_name: str
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
    race_ethnicity: str | None = None
    religion: str | None = None
    political_view: str | None = None
    premium_until: datetime | None = None
    race_filter: list[str] = []
    religion_filter: list[str] = []
    # Raw storage column, never serialized directly — see the premium_filters
    # computed_field below, which parses this into the typed shape the
    # client actually consumes.
    premium_filters_json: str | None = Field(default=None, exclude=True)
    height_cm: int | None = None
    occupation: str | None = None
    education: str | None = None
    hometown: str | None = None
    smoking: str | None = None
    cannabis: str | None = None
    exercise_frequency: str | None = None
    relationship_goal: str | None = None
    wants_kids: str | None = None
    has_kids: str | None = None
    interests: list[str] = []
    languages: list[str] = []
    updated_at: datetime
    photos: list[PhotoOut] = []

    @field_validator("race_filter", "religion_filter", "interests", "languages", mode="before")
    @classmethod
    def _split_comma_list(cls, value: object) -> list[str]:
        # Stored as a single comma-separated column (see models/profile.py);
        # the API surface is a plain list so mobile doesn't need to know that.
        if value is None or isinstance(value, list):
            return value or []
        return [v for v in str(value).split(",") if v]

    @computed_field
    @property
    def is_premium_member(self) -> bool:
        if self.premium_until is None:
            return False
        premium_until = self.premium_until
        if premium_until.tzinfo is None:
            premium_until = premium_until.replace(tzinfo=timezone.utc)
        return premium_until > datetime.now(timezone.utc)

    @computed_field
    @property
    def premium_filters(self) -> PremiumFilters:
        if not self.premium_filters_json:
            return PremiumFilters()
        try:
            return PremiumFilters(**json.loads(self.premium_filters_json))
        except (ValueError, TypeError):
            # Malformed stored JSON should never 500 a profile read — treat
            # it the same as "no filters set" rather than crashing.
            return PremiumFilters()


class PresignRequest(BaseModel):
    # One video slot per profile (position convention enforced by the
    # mobile UI, not here) alongside up to 9 photo slots.
    content_type: str = Field(pattern="^(image/(jpeg|png|webp)|video/mp4)$")
    position: int = Field(ge=0, le=8)


class PresignResponse(BaseModel):
    upload_url: str
    gcs_object_path: str


class PhotoConfirmRequest(BaseModel):
    gcs_object_path: str
    position: int = Field(ge=0, le=8)


class IncognitoUpdate(BaseModel):
    is_incognito: bool


class PremiumFilterUpdate(BaseModel):
    # Premium-gated (402 if the caller isn't an active premium member — see
    # routers/profiles.py::set_premium_filters). Empty/omitted list (or null
    # height bound) clears that filter, showing everyone again regardless.
    # race_filter/religion_filter are their own DB columns (pre-existing);
    # everything else here is stored as one JSON blob (Profile.
    # premium_filters_json) — see that column's comment for why.
    race_filter: list[str] = Field(default_factory=list)
    religion_filter: list[str] = Field(default_factory=list)
    political_view_filter: list[str] = Field(default_factory=list)
    exercise_frequency_filter: list[str] = Field(default_factory=list)
    smoking_filter: list[str] = Field(default_factory=list)
    cannabis_filter: list[str] = Field(default_factory=list)
    relationship_goal_filter: list[str] = Field(default_factory=list)
    wants_kids_filter: list[str] = Field(default_factory=list)
    has_kids_filter: list[str] = Field(default_factory=list)
    height_min: int | None = Field(default=None, ge=50, le=272)
    height_max: int | None = Field(default=None, ge=50, le=272)


class AgeFilterUpdate(BaseModel):
    """Free for everyone — unlike PremiumFilterUpdate above, no premium
    gating (see routers/profiles.py::set_age_filter)."""

    min_age_pref: int = Field(default=18, ge=18, le=99)
    max_age_pref: int = Field(default=99, ge=18, le=99)


class TravelModeRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    duration_hours: int = Field(default=24, ge=1, le=24 * 30)
