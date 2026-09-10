import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.services.storage_service import build_public_url


class MomentCreate(BaseModel):
    image_object_path: str
    caption: str | None = Field(default=None, max_length=280)


class MomentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    image_object_path: str = Field(exclude=True)
    caption: str | None = None
    created_at: datetime

    @computed_field
    @property
    def image_url(self) -> str:
        return build_public_url(self.image_object_path)
