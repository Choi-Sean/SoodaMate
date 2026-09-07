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


class FaceVerificationStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    submitted_at: datetime | None = None


class FaceVerificationAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    gcs_object_path: str = Field(exclude=True)  # selfie
    id_photo_object_path: str | None = Field(exclude=True, default=None)
    status: str
    submitted_at: datetime
    display_name: str | None = None

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
