import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.services.storage_service import build_public_url

# Same 5 languages the rest of the app is localized into (i18n, push_i18n) —
# a translation target outside this set would just be an untranslated app
# around it, so the picker never offers more than this.
SUPPORTED_TRANSLATE_LANGUAGES = ("ko", "en", "es", "zh", "ja")


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


class TranslateMessageRequest(BaseModel):
    target_language: str = Field(pattern="^(" + "|".join(SUPPORTED_TRANSLATE_LANGUAGES) + ")$")


class TranslateMessageOut(BaseModel):
    translated_content: str
    target_language: str


class ImagePresignRequest(BaseModel):
    """Shared by /uploads/presign-chat-image and /uploads/presign-story-image
    — images only (jpeg/png/webp), never video, never an arbitrary file."""

    content_type: str = Field(pattern="^image/(jpeg|png|webp)$")
