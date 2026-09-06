import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SwipeRequest(BaseModel):
    to_user_id: uuid.UUID


class SwipeResponse(BaseModel):
    matched: bool
    match_id: uuid.UUID | None = None


class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    other_user_id: uuid.UUID
    other_display_name: str
    other_photo_url: str | None = None
    matched_at: datetime
    is_message_restricted: bool = False
    can_send_first_message: bool = True
    first_message_deadline: datetime | None = None


class SwipeLimitOut(BaseModel):
    remaining: int
    limit: int
    resets_at: datetime | None = None
