import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    is_active: bool = True
    # Blind chat (see services/blind_chat_service.py). other_display_name/
    # other_photo_url above are already masked (a 1-char + "***" name, null
    # photo) by match_service whenever is_blind and not blind_revealed —
    # every existing screen that just shows those two fields is safe by
    # construction and needs no blind-aware branching.
    is_blind: bool = False
    blind_categories: list[str] = []
    blind_revealed: bool = False
    can_request_reveal: bool = False
    has_incoming_reveal_request: bool = False
    reveal_requested_by_me: bool = False


class SwipeLimitOut(BaseModel):
    remaining: int
    limit: int
    resets_at: datetime | None = None
    unlimited: bool = False


class BlindChatQueueRequest(BaseModel):
    categories: list[str] = Field(min_length=1, max_length=10)


class BlindChatQueueStatusOut(BaseModel):
    """status is "waiting" (still in the queue), "matched" (paired within
    the last few minutes — match_id is set), or "idle" (not queued, no
    recent pairing — e.g. never joined, or canceled)."""

    status: str
    match_id: uuid.UUID | None = None


class IcebreakerOut(BaseModel):
    """type is one of shared_kcontent/shared_interest/shared_language_exchange/
    shared_language/generic; key names the specific shared tag (an
    interests.<key>/kcontent.<key> i18n key) or is None when there's nothing
    to point at (shared_language_exchange/generic) — see
    services/icebreaker_service.py. The suggestion's actual display text is
    entirely a mobile i18n concern (chat.icebreaker.<type>), interpolating
    key's translated label."""

    type: str
    key: str | None = None
