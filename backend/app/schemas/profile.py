import json
import uuid
from datetime import date, datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.moment import MomentOut
from app.services.storage_service import build_public_url
from app.utils.premium import is_premium


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
    """The premium_filters_json-backed dimensions only (religion_filter
    stays a top-level ProfileOut field, pre-existing/unchanged). height_min/
    height_max used to live here too; height is a free Basic-tab filter now
    (see Profile.height_filter_min/max + BasicFilters below) with its own
    dedicated columns, not this JSON blob."""

    political_view_filter: list[str] = []
    exercise_frequency_filter: list[str] = []
    smoking_filter: list[str] = []
    cannabis_filter: list[str] = []
    relationship_goal_filter: list[str] = []
    wants_kids_filter: list[str] = []
    has_kids_filter: list[str] = []


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)
    legal_first_name: str = Field(min_length=1, max_length=50)
    birth_date: date
    gender: str = Field(pattern="^(male|female|other)$")
    interested_in: str = Field(pattern="^(male|female|other|all)$")
    open_to_language_exchange: bool = False
    bio: str | None = Field(default=None, max_length=1000)
    bio2: str | None = Field(default=None, max_length=1000)
    bio3: str | None = Field(default=None, max_length=1000)
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
    k_content_tags: list[str] = Field(default_factory=list)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    display_name: str
    legal_first_name: str
    birth_date: date
    gender: str
    interested_in: str
    open_to_language_exchange: bool = False
    bio: str | None
    bio2: str | None = None
    bio3: str | None = None
    location_lat: float | None
    location_lng: float | None
    min_age_pref: int
    max_age_pref: int
    max_distance_km: int
    is_profile_complete: bool
    verified_badge: str | None = None
    face_verified: bool = False
    superlike_credits: int = 0
    boost_credits: int = 0
    boost_active_until: datetime | None = None
    ai_match_credits: int = 0
    unlimited_matching_until: datetime | None = None
    is_incognito: bool = False
    travel_lat: float | None = None
    travel_lng: float | None = None
    travel_expires_at: datetime | None = None
    race_ethnicity: str | None = None
    religion: str | None = None
    political_view: str | None = None
    premium_until: datetime | None = None
    billing_cycle: str | None = None
    subscription_price_cents: int | None = None
    cancel_at_period_end: bool = False
    # race_filter is a free Basic-tab filter (not premium-gated) despite
    # sharing history/column-naming with religion_filter below, which is
    # still premium — see Profile.race_filter's comment.
    race_filter: list[str] = []
    religion_filter: list[str] = []
    height_filter_min: int | None = None
    height_filter_max: int | None = None
    languages_filter: list[str] = []
    interests_filter: list[str] = []
    verified_only: bool = False
    expand_distance_if_low: bool = True
    expand_others_if_low: bool = True
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
    k_content_tags: list[str] = []
    k_content_filter: list[str] = []
    updated_at: datetime
    photos: list[PhotoOut] = []
    moments: list[MomentOut] = []

    @field_validator(
        "race_filter",
        "religion_filter",
        "interests",
        "languages",
        "languages_filter",
        "interests_filter",
        "k_content_tags",
        "k_content_filter",
        mode="before",
    )
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
        return is_premium(self.premium_until)

    # Mirrors blind_chat_service.is_unlimited_matching_active exactly (same
    # premium-or-topup-still-running check) — duplicated here rather than
    # imported since that function takes the ORM Profile, not this schema,
    # and the check itself is only two lines.
    @computed_field
    @property
    def is_unlimited_matching_active(self) -> bool:
        if self.is_premium_member:
            return True
        until = self.unlimited_matching_until
        if until is None:
            return False
        # MSSQL sometimes hands back a naive datetime despite the column
        # being DateTime(timezone=True) — same normalization as
        # blind_chat_service.is_unlimited_matching_active.
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return until > datetime.now(timezone.utc)

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
    # mobile UI, not here) alongside up to 6 photo slots.
    content_type: str = Field(pattern="^(image/(jpeg|png|webp)|video/mp4)$")
    # 7 slots (0-6): up to 6 photos plus the one video slot.
    position: int = Field(ge=0, le=6)


class PresignResponse(BaseModel):
    upload_url: str
    gcs_object_path: str


class PhotoConfirmRequest(BaseModel):
    gcs_object_path: str
    # 7 slots (0-6): up to 6 photos plus the one video slot.
    position: int = Field(ge=0, le=6)


class PhotoReorderRequest(BaseModel):
    photo_ids: list[uuid.UUID] = Field(min_length=1)


class IncognitoUpdate(BaseModel):
    is_incognito: bool


class PremiumFilterUpdate(BaseModel):
    # Premium-gated (402 if the caller isn't an active premium member — see
    # routers/profiles.py::set_premium_filters). Empty list clears that
    # filter, showing everyone again regardless. religion_filter is its own
    # DB column (pre-existing); everything else here is stored as one JSON
    # blob (Profile.premium_filters_json) — see that column's comment for
    # why. race_filter/height moved to BasicFilterUpdate below — they're
    # free now.
    religion_filter: list[str] = Field(default_factory=list)
    political_view_filter: list[str] = Field(default_factory=list)
    exercise_frequency_filter: list[str] = Field(default_factory=list)
    smoking_filter: list[str] = Field(default_factory=list)
    cannabis_filter: list[str] = Field(default_factory=list)
    relationship_goal_filter: list[str] = Field(default_factory=list)
    wants_kids_filter: list[str] = Field(default_factory=list)
    has_kids_filter: list[str] = Field(default_factory=list)


class AgeFilterUpdate(BaseModel):
    """Free for everyone — unlike PremiumFilterUpdate above, no premium
    gating (see routers/profiles.py::set_age_filter)."""

    min_age_pref: int = Field(default=18, ge=18, le=99)
    max_age_pref: int = Field(default=99, ge=18, le=99)


class BasicFilterUpdate(BaseModel):
    """Every Basic-tab filter dimension, all free (no premium check — see
    routers/profiles.py::set_basic_filters). Age has its own pre-existing
    endpoint (AgeFilterUpdate/set_age_filter) and isn't repeated here."""

    max_distance_km: int = Field(default=50, ge=1, le=500)
    race_filter: list[str] = Field(default_factory=list)
    height_min: int | None = Field(default=None, ge=50, le=272)
    height_max: int | None = Field(default=None, ge=50, le=272)
    languages_filter: list[str] = Field(default_factory=list)
    interests_filter: list[str] = Field(default_factory=list)
    k_content_filter: list[str] = Field(default_factory=list)
    verified_only: bool = False
    language_exchange_only: bool = False
    expand_distance_if_low: bool = True
    expand_others_if_low: bool = True


class TravelModeRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    duration_hours: int = Field(default=24, ge=1, le=24 * 30)
