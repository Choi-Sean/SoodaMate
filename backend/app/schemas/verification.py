import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

from app.services.storage_service import build_admin_view_url


class VerificationStartRequest(BaseModel):
    kind: str = Field(pattern="^(work|school)$")
    email: EmailStr


class VerificationConfirmRequest(BaseModel):
    kind: str = Field(pattern="^(work|school)$")
    code: str = Field(min_length=6, max_length=6)


class FacePresignRequest(BaseModel):
    content_type: str = Field(pattern="^image/(jpeg|png|webp)$")
    # Doesn't change how/where the object is stored (the path is a random
    # UUID either way) — just documents intent in the object key for anyone
    # debugging storage directly.
    kind: str = Field(pattern="^(selfie|id_photo)$", default="selfie")


class FaceVerificationSubmitRequest(BaseModel):
    selfie_object_path: str
    id_photo_object_path: str


# Fixed set the admin dropdown at soodamate.com/verify picks from — the
# mobile app has its own translated copy for each key (see
# faceVerification.rejectReasons.* in the locale files) so a rejected user
# sees the reason in *their* app language, not whichever language the admin
# happened to be reading English in. "other" is the one key whose paired
# `reason` text is shown verbatim instead of being looked up/translated.
REJECTION_REASON_KEYS = (
    "selfie_id_mismatch",
    "id_blurry",
    "selfie_blurry",
    "name_mismatch",
    "id_invalid",
    "incomplete",
    "other",
)


class FaceVerificationRejectRequest(BaseModel):
    reason_key: str = Field(pattern="^(" + "|".join(REJECTION_REASON_KEYS) + ")$")
    # The admin-facing English label for fixed keys (for the Rejected tab's
    # own listing); the actual freeform note when reason_key is "other".
    reason: str = Field(min_length=1, max_length=500)


class FaceVerificationStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    submitted_at: datetime | None = None
    rejection_reason: str | None = None
    rejection_reason_key: str | None = None


class FaceVerificationAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    gcs_object_path: str = Field(exclude=True)  # selfie
    id_photo_object_path: str | None = Field(exclude=True, default=None)
    status: str
    submitted_at: datetime
    display_name: str | None = None
    rejection_reason: str | None = None
    rejection_reason_key: str | None = None

    # Presigned, time-limited GET URLs generated per-request — never the
    # public photo-bucket URL convention (see FaceVerification's docstring).
    @computed_field
    @property
    def selfie_view_url(self) -> str:
        return build_admin_view_url(self.gcs_object_path)

    @computed_field
    @property
    def id_photo_view_url(self) -> str | None:
        return build_admin_view_url(self.id_photo_object_path) if self.id_photo_object_path else None
