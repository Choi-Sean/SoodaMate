import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Profile(Base):
    __tablename__ = "Profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", Uuid(as_uuid=True), ForeignKey("Users.Id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column("DisplayName", Unicode(50), nullable=False)
    # Required, but never shown to other users (see display_name for that) —
    # collected for identity/legal purposes only.
    legal_first_name: Mapped[str] = mapped_column("LegalFirstName", Unicode(50), nullable=False)
    birth_date: Mapped[date] = mapped_column("BirthDate", Date, nullable=False)
    gender: Mapped[str] = mapped_column("Gender", Unicode(10), nullable=False)  # 'male' | 'female' | 'other'
    interested_in: Mapped[str] = mapped_column(
        "InterestedIn", Unicode(10), nullable=False
    )  # 'male' | 'female' | 'other' | 'all'
    bio: Mapped[str | None] = mapped_column("Bio", UnicodeText, nullable=True)
    location_lat: Mapped[float | None] = mapped_column("LocationLat", nullable=True)
    location_lng: Mapped[float | None] = mapped_column("LocationLng", nullable=True)
    min_age_pref: Mapped[int] = mapped_column("MinAgePref", Integer, default=18, nullable=False)
    max_age_pref: Mapped[int] = mapped_column("MaxAgePref", Integer, default=99, nullable=False)
    max_distance_km: Mapped[int] = mapped_column("MaxDistanceKm", Integer, default=50, nullable=False)
    is_profile_complete: Mapped[bool] = mapped_column("IsProfileComplete", Boolean, default=False, nullable=False)

    # Phase 16 — employment/school verification badge (one active slot for v1)
    verified_badge: Mapped[str | None] = mapped_column(
        "VerifiedBadge", Unicode(20), nullable=True
    )  # 'work' | 'school' | None

    # Phase 17 — superswipe/boost (paid, RevenueCat)
    superlike_credits: Mapped[int] = mapped_column("SuperlikeCredits", Integer, default=0, nullable=False)
    free_superlike_used_on: Mapped[date | None] = mapped_column("FreeSuperlikeUsedOn", Date, nullable=True)
    boost_credits: Mapped[int] = mapped_column("BoostCredits", Integer, default=0, nullable=False)
    boost_active_until: Mapped[datetime | None] = mapped_column(
        "BoostActiveUntil", DateTime(timezone=True), nullable=True
    )

    # Phase 18 — incognito + travel mode (free, not paywalled per product decision)
    is_incognito: Mapped[bool] = mapped_column("IsIncognito", Boolean, default=False, nullable=False)
    travel_lat: Mapped[float | None] = mapped_column("TravelLat", nullable=True)
    travel_lng: Mapped[float | None] = mapped_column("TravelLng", nullable=True)
    travel_expires_at: Mapped[datetime | None] = mapped_column(
        "TravelExpiresAt", DateTime(timezone=True), nullable=True
    )

    # Collected at signup for every user (free), shown on the profile like
    # gender/bio — not paywalled to set. Free-text category strings rather
    # than an enum since the allowed option lists are UI-owned, not enforced
    # server-side.
    race_ethnicity: Mapped[str | None] = mapped_column("RaceEthnicity", Unicode(50), nullable=True)
    religion: Mapped[str | None] = mapped_column("Religion", Unicode(50), nullable=True)
    political_view: Mapped[str | None] = mapped_column("PoliticalView", Unicode(50), nullable=True)

    # Premium membership: gates race_filter/religion_filter below. A
    # one-time Stripe purchase (like superlike/boost) extends this instead
    # of a true recurring Stripe Subscription — see payment_service.py.
    premium_until: Mapped[datetime | None] = mapped_column("PremiumUntil", DateTime(timezone=True), nullable=True)
    # Comma-separated allow-lists of race_ethnicity/religion values to
    # restrict Discover to — only ever applied by discovery_service if
    # is_premium_member(profile) is true; the free tier only gets the
    # existing age/distance filters above.
    race_filter: Mapped[str | None] = mapped_column("RaceFilter", Unicode(255), nullable=True)
    religion_filter: Mapped[str | None] = mapped_column("ReligionFilter", Unicode(255), nullable=True)
    # Every other premium filter dimension (political_view/exercise_frequency/
    # smoking/cannabis/relationship_goal/wants_kids/has_kids as lists, plus
    # height_min/height_max) as one JSON blob rather than 9 more dedicated
    # columns — same premium gating as race_filter/religion_filter above,
    # just parsed in Python instead of matched in SQL param binding. See
    # services/discovery_service.py for how it's applied and
    # schemas/profile.py's PremiumFilters for the typed shape.
    premium_filters_json: Mapped[str | None] = mapped_column("PremiumFiltersJson", Unicode(2000), nullable=True)

    # Optional extended profile fields — all free-text category strings
    # (like race_ethnicity/religion above), collected at signup but not
    # filterable/searchable in v1. interests/languages are comma-separated
    # lists, same storage convention as race_filter/religion_filter.
    height_cm: Mapped[int | None] = mapped_column("HeightCm", Integer, nullable=True)
    occupation: Mapped[str | None] = mapped_column("Occupation", Unicode(100), nullable=True)
    education: Mapped[str | None] = mapped_column("Education", Unicode(100), nullable=True)
    hometown: Mapped[str | None] = mapped_column("Hometown", Unicode(100), nullable=True)
    smoking: Mapped[str | None] = mapped_column("Smoking", Unicode(30), nullable=True)
    cannabis: Mapped[str | None] = mapped_column("Cannabis", Unicode(30), nullable=True)
    exercise_frequency: Mapped[str | None] = mapped_column("ExerciseFrequency", Unicode(30), nullable=True)
    relationship_goal: Mapped[str | None] = mapped_column("RelationshipGoal", Unicode(30), nullable=True)
    wants_kids: Mapped[str | None] = mapped_column("WantsKids", Unicode(30), nullable=True)
    has_kids: Mapped[str | None] = mapped_column("HasKids", Unicode(30), nullable=True)
    interests: Mapped[str | None] = mapped_column("Interests", Unicode(500), nullable=True)
    languages: Mapped[str | None] = mapped_column("Languages", Unicode(255), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        "UpdatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Photo(Base):
    __tablename__ = "Photos"
    __table_args__ = (UniqueConstraint("UserId", "Position", name="uq_photo_position"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    gcs_object_path: Mapped[str] = mapped_column("GcsObjectPath", Unicode(512), nullable=False)
    position: Mapped[int] = mapped_column("Position", SmallInteger, nullable=False, default=0)
    # "photo" | "video" — derived server-side from the upload's extension
    # (routers/profiles.py::confirm_photo), never trusted from client input.
    # server_default so ALTER TABLE ADD backfills existing rows as photos.
    media_type: Mapped[str] = mapped_column(
        "MediaType", Unicode(10), nullable=False, server_default="photo", default="photo"
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
