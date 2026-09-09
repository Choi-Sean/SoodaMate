import uuid
from datetime import datetime

from pydantic import BaseModel, Field, computed_field

from app.services.storage_service import build_public_url


class CoupleStoryCreate(BaseModel):
    match_id: uuid.UUID
    story_text: str = Field(min_length=1, max_length=2000)
    photo_object_path: str | None = None


class CoupleStoryReportCreate(BaseModel):
    reason: str = Field(min_length=1, max_length=100)


class CoupleStoryOut(BaseModel):
    """Built by hand in routers/couple_stories.py (not model_validate'd
    directly off the row) since author_display_name/peer_display_name come
    from each side's Profile, not the CoupleStory row itself. Deliberately
    never carries either matched user's own dating-profile photo — only the
    optional couple photo they chose to attach — so the public community
    feed can't be used to browse individual profile photos outside of
    Discover."""

    id: uuid.UUID
    match_id: uuid.UUID
    author_id: uuid.UUID
    peer_id: uuid.UUID
    author_display_name: str
    peer_display_name: str
    story_text: str
    photo_object_path: str | None = None
    status: str
    created_at: datetime
    published_at: datetime | None = None

    @computed_field
    @property
    def photo_url(self) -> str | None:
        return build_public_url(self.photo_object_path) if self.photo_object_path else None
