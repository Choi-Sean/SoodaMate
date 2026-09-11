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
    # A trait of the profile itself (like gender/interested_in above), not a
    # filter someone else applies — shown on the candidate card so two
    # people who both want to practice each other's language can spot that
    # before ever swiping. See language_exchange_only below for the
    # Basic-tab filter that searches on this.
    open_to_language_exchange: Mapped[bool] = mapped_column(
        "OpenToLanguageExchange", Boolean, default=False, nullable=False
    )
    bio: Mapped[str | None] = mapped_column("Bio", UnicodeText, nullable=True)
    # Two more free-text prompts alongside the main bio (Hinge/Bumble-style
    # "a few more things about me"), same nullable/unbounded-length shape —
    # no separate prompt/question per slot in v1, just more room to write.
    bio2: Mapped[str | None] = mapped_column("Bio2", UnicodeText, nullable=True)
    bio3: Mapped[str | None] = mapped_column("Bio3", UnicodeText, nullable=True)
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

    # Blind chat monetization (see services/blind_chat_service.py). Consumed
    # 1-per-instant-match by POST /blind-chat/ai-match, same consumable-
    # credit shape as superlike_credits above. unlimited_matching_until is a
    # fixed-duration top-up (extends like a credit, not a cancellable
    # subscription) rather than reusing premium_until's Stripe-subscription
    # machinery — simpler because there's nothing to cancel, only more time
    # to add; is_premium members already get this for free (see
    # blind_chat_service.is_unlimited_matching_active).
    ai_match_credits: Mapped[int] = mapped_column("AiMatchCredits", Integer, default=0, nullable=False)
    unlimited_matching_until: Mapped[datetime | None] = mapped_column(
        "UnlimitedMatchingUntil", DateTime(timezone=True), nullable=True
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

    # Premium membership: gates race_filter/religion_filter below.
    # Originally a one-time Stripe purchase extending this date (like
    # superlike/boost credits); membership_monthly/membership_yearly are now
    # real recurring Stripe Subscriptions instead — see payment_service.py.
    # The four fields below are only ever set for that real-subscription
    # path; a premium_until granted any other way (a one-time top-up, or a
    # manually-granted comp) leaves them all NULL, which the profile schema
    # and mobile UI both read as "no subscription to show billing info for
    # or cancel" rather than fabricating a billing date that doesn't exist.
    premium_until: Mapped[datetime | None] = mapped_column("PremiumUntil", DateTime(timezone=True), nullable=True)
    billing_cycle: Mapped[str | None] = mapped_column("BillingCycle", Unicode(10), nullable=True)  # 'monthly' | 'yearly'
    subscription_price_cents: Mapped[int | None] = mapped_column("SubscriptionPriceCents", Integer, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column("StripeSubscriptionId", Unicode(255), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column("CancelAtPeriodEnd", Boolean, default=False, nullable=False)
    # Comma-separated allow-list of religion values — still premium-only,
    # applied by discovery_service only if is_premium_member(profile).
    religion_filter: Mapped[str | None] = mapped_column("ReligionFilter", Unicode(255), nullable=True)

    # --- Basic (free) filters, set via PUT /profiles/me/basic-filters ---
    # race_filter used to live in the premium bucket alongside
    # religion_filter above; it's a free/Basic-tab filter now (moved to
    # match Bumble's own free-vs-premium split), so it's grouped with the
    # rest of the free filters here instead, even though its column name
    # is unchanged for migration simplicity.
    race_filter: Mapped[str | None] = mapped_column("RaceFilter", Unicode(255), nullable=True)
    height_filter_min: Mapped[int | None] = mapped_column("HeightFilterMin", Integer, nullable=True)
    height_filter_max: Mapped[int | None] = mapped_column("HeightFilterMax", Integer, nullable=True)
    languages_filter: Mapped[str | None] = mapped_column("LanguagesFilter", Unicode(255), nullable=True)
    interests_filter: Mapped[str | None] = mapped_column("InterestsFilter", Unicode(500), nullable=True)
    verified_only: Mapped[bool] = mapped_column("VerifiedOnly", Boolean, default=False, nullable=False)
    # Restricts candidates to open_to_language_exchange == True above.
    language_exchange_only: Mapped[bool] = mapped_column(
        "LanguageExchangeOnly", Boolean, default=False, nullable=False
    )
    # Bumble's own two independent "if I run out" toggles: relax the
    # distance cap first, and only if that's still not enough, drop every
    # optional Basic filter above (age/height/distance/race/languages/
    # interests/verified) and backfill with anyone else — see
    # discovery_service.get_candidates' two-stage fallback. Both default
    # True to match Bumble's own default-on state.
    expand_distance_if_low: Mapped[bool] = mapped_column("ExpandDistanceIfLow", Boolean, default=True, nullable=False)
    expand_others_if_low: Mapped[bool] = mapped_column("ExpandOthersIfLow", Boolean, default=True, nullable=False)
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
    # K-content taste tags (K-drama/K-pop/webtoon/K-movie favorites) — same
    # comma-separated storage convention as interests/languages above, own
    # curated key list (mobile/src/constants/kContentTags.ts) rather than
    # reusing INTEREST_KEYS, so the two pickers can evolve independently.
    # Free to set (like interests); k_content_filter below is the matching
    # free Basic-tab filter, same relationship as interests/interests_filter.
    k_content_tags: Mapped[str | None] = mapped_column("KContentTags", Unicode(500), nullable=True)
    k_content_filter: Mapped[str | None] = mapped_column("KContentFilter", Unicode(500), nullable=True)
    # Set True only by an admin approving a FaceVerification row below —
    # never writable through the regular profile-update endpoint.
    face_verified: Mapped[bool] = mapped_column(
        "FaceVerified", Boolean, nullable=False, default=False, server_default="0"
    )

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


class FaceVerification(Base):
    """One selfie + ID photo submission for the verification badge, reviewed
    by hand at soodamate.com/verify (an admin-only static page) side by side
    rather than an automated document-forensics/liveness vendor (Stripe
    Identity/Veriff/Persona etc. — deliberately deferred until real
    signup volume makes manual review a bottleneck; see docs/ARCHITECTURE.md).
    Both photos live at an unguessable random path in the same R2 bucket
    profile photos use (technically reachable if someone guessed the exact
    path — a known limitation flagged for a follow-up private bucket) rather
    than served through the public photo URL convention.
    id_photo_object_path is nullable only because rows created before this
    field existed won't have one — every new submission always sets it."""

    __tablename__ = "FaceVerifications"

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    gcs_object_path: Mapped[str] = mapped_column("GcsObjectPath", Unicode(512), nullable=False)  # selfie
    id_photo_object_path: Mapped[str | None] = mapped_column("IdPhotoObjectPath", Unicode(512), nullable=True)
    # "pending" | "approved" | "rejected"
    status: Mapped[str] = mapped_column("Status", Unicode(20), nullable=False, default="pending")
    submitted_at: Mapped[datetime] = mapped_column("SubmittedAt", DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column("ReviewedAt", DateTime(timezone=True), nullable=True)
    # Set on reject, shown back to the user so they know what to fix before
    # resubmitting. rejection_reason_key is one of a fixed set the admin
    # picks from soodamate.com/verify's dropdown (or "other") - the mobile
    # app looks it up in its own i18n so the user sees it in *their*
    # selected app language, not whatever language the admin happened to
    # pick it in. rejection_reason is the admin-facing English text (also
    # the literal text shown to the user when the key is "other", since a
    # freeform note can't be translated). Both cleared on a fresh submission
    # or approve.
    rejection_reason_key: Mapped[str | None] = mapped_column("RejectionReasonKey", Unicode(50), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column("RejectionReason", Unicode(500), nullable=True)
