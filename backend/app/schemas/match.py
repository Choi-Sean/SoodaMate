import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.blind_chat_feedback import BLIND_CHAT_FEEDBACK_TAG_KEYS


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
    # Shown regardless of is_blind/blind_revealed — unlike name/photo above,
    # a bio was never treated as identifying enough to withhold during an
    # anonymous chat (product decision), so _build_match_out populates these
    # outside its hide_identity branch.
    other_bio: str | None = None
    other_bio2: str | None = None
    other_bio3: str | None = None
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
    # Optional per-session choices that TAKE PRECEDENCE over the profile's own
    # stored gender/age preferences for this queue session (the client
    # defaults them to the profile's values, so a value that differs from the
    # profile is a deliberate override) — None means "use my profile
    # defaults," same convention as the Basic filters' optional fields in
    # profiles.py. max_distance_km of 0/None means no distance cap for this
    # session.
    gender: str | None = None  # 'male' | 'female' | 'other' | 'all', the candidate gender wanted
    min_age: int | None = None
    max_age: int | None = None
    max_distance_km: int | None = None

    @model_validator(mode="after")
    def _age_range_must_be_ordered(self) -> "BlindChatQueueRequest":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age cannot be greater than max_age")
        return self


class BlindChatQueueStatusOut(BaseModel):
    """status is "waiting" (still in the queue), "matched" (paired within
    the last few minutes — match_id is set), or "idle" (not queued, no
    recent pairing — e.g. never joined, or canceled)."""

    status: str
    match_id: uuid.UUID | None = None


class BlindChatLimitOut(BaseModel):
    """Mirrors SwipeLimitOut's shape — see
    blind_chat_service.get_blind_chat_limit_status."""

    remaining: int
    limit: int
    resets_at: datetime | None = None
    unlimited: bool = False
    # Whether today's rewarded-ad bonus match hasn't been claimed yet — lets
    # the client decide whether to show the "watch ad for +1" CTA at all.
    # Always False when unlimited (nothing to claim).
    bonus_available: bool = False


class AiMatchRequest(BaseModel):
    categories: list[str] = Field(min_length=1, max_length=10)
    # Same per-session choices as BlindChatQueueRequest — the AI match must
    # honor the gender/age/distance picked on the match screen, not silently
    # fall back to the profile defaults.
    gender: str | None = None
    min_age: int | None = None
    max_age: int | None = None
    max_distance_km: int | None = None

    @model_validator(mode="after")
    def _age_range_must_be_ordered(self) -> "AiMatchRequest":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age cannot be greater than max_age")
        return self


class AiMatchOut(BaseModel):
    """found=False means no compatible member is available right now — the
    credit is never consumed in that case (see blind_chat_service.find_ai_match),
    so match is always None when found is False."""

    found: bool
    match: MatchOut | None = None


class BlindChatFeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list, max_length=len(BLIND_CHAT_FEEDBACK_TAG_KEYS))
    # Only meaningful (and only ever stored) alongside "other" in tags —
    # never sent to the LLM prompt, see BlindChatFeedback's own docstring.
    comment: str | None = Field(default=None, max_length=100)

    @field_validator("tags")
    @classmethod
    def _tags_must_be_known(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - set(BLIND_CHAT_FEEDBACK_TAG_KEYS))
        if invalid:
            raise ValueError(f"unknown feedback tag(s): {invalid}")
        return value

    @model_validator(mode="after")
    def _comment_requires_other_tag(self) -> "BlindChatFeedbackCreate":
        if self.comment and "other" not in self.tags:
            raise ValueError("comment is only allowed alongside the 'other' tag")
        return self


class BlindChatFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rating: int
    tags: list[str]
    comment: str | None = None


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
