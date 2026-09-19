import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, Unicode, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, utc_now, utc_now_default

# Signal only — never shown to the rated user, never used for moderation
# (that's Report's job). Deliberately not a superset/copy of Report's
# reasons: this measures match-compatibility fit, not policy violations.
BLIND_CHAT_FEEDBACK_TAG_KEYS: tuple[str, ...] = (
    "kind",
    "great_conversation",
    "similar_interests",
    "awkward",
    "uncomfortable",
    "no_show",
    "other",
)


class BlindChatFeedback(Base):
    """Optional post-chat rating of a blind-chat partner, folded into future
    AI Match ranking as an aggregate signal (see llm_match_service.py) — the
    individual row, and especially `comment`, is never shown to the rated
    user or to whoever a future match pairs them with; only the aggregate
    (average rating + tag frequency) is. One row per (match, rater) — a
    rater changing their mind re-submits over the same row (see
    blind_chat_service.submit_feedback's try_insert-then-update) rather than
    stacking a second one.

    match_id cascades from Matches (a single, unambiguous path); rater_user_id/
    rated_user_id intentionally don't (same multi-cascade-path reasoning as
    CoupleStory.author_id/peer_id — MSSQL rejects two CASCADE paths to the
    same table). Harmless in practice: routers/account.py always deletes a
    departing user's Matches first, which already cascades this row away via
    match_id before the user row itself is ever removed."""

    __tablename__ = "BlindChatFeedback"
    __table_args__ = (UniqueConstraint("MatchId", "RaterUserId", name="uq_blind_feedback_rater"),)

    id: Mapped[uuid.UUID] = mapped_column(
        "Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        "MatchId", ForeignKey("Matches.Id", ondelete="CASCADE"), nullable=False
    )
    rater_user_id: Mapped[uuid.UUID] = mapped_column(
        "RaterUserId", ForeignKey("Users.Id"), nullable=False
    )
    rated_user_id: Mapped[uuid.UUID] = mapped_column(
        "RatedUserId", ForeignKey("Users.Id"), nullable=False
    )
    rating: Mapped[int] = mapped_column("Rating", SmallInteger, nullable=False)  # 1-5
    # Comma-separated subset of BLIND_CHAT_FEEDBACK_TAG_KEYS.
    tags: Mapped[str] = mapped_column("Tags", Unicode(255), nullable=False, default="")
    # Only ever set alongside "other" in tags — see schemas.blind_chat's
    # validator; free text, so kept out of the LLM prompt entirely (only the
    # structured rating/tags feed AI Match — see llm_match_service.py).
    comment: Mapped[str | None] = mapped_column("Comment", Unicode(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime(timezone=True), server_default=utc_now_default, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        "UpdatedAt",
        DateTime(timezone=True),
        server_default=utc_now_default,
        default=utc_now,
        onupdate=utc_now,
    )
