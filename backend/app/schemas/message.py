import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.services.storage_service import build_public_url


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    message_type: str = "text"
    image_object_path: str | None = None
    original_language: str | None = None
    translated_content: str | None = None
    translated_language: str | None = None
    sent_at: datetime
    delivered_at: datetime | None
    read_at: datetime | None

    @computed_field
    @property
    def image_url(self) -> str | None:
        return build_public_url(self.image_object_path) if self.image_object_path else None


class ImagePresignRequest(BaseModel):
    """Shared by /uploads/presign-chat-image and /uploads/presign-story-image
    — images only (jpeg/png/webp), never video, never an arbitrary file."""

    content_type: str = Field(pattern="^image/(jpeg|png|webp)$")
