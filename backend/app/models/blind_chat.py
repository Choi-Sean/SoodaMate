import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BlindChatQueueEntry(Base):
    """One user currently waiting to be randomly paired for blind chat — see
    services/blind_chat_service.py. Single FK to Users with ondelete=CASCADE
    (no multi-cascade-path ambiguity, unlike Match/Swipe) — a deleted
    account's queue entry just disappears with it, nothing else references
    this table. Unique on user_id: a second POST /blind-chat/queue call
    while already waiting is a no-op, not a second entry."""

    __tablename__ = "BlindChatQueue"

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False, unique=True
    )
    # Comma-separated category keys (mobile/src/constants/blindChatCategories.ts
    # owns the canonical list, same "UI-owned, not enforced server-side"
    # convention as Profile.interests/race_ethnicity) selected for *this*
    # queue session — re-queueing can pick a different set each time.
    categories: Mapped[str] = mapped_column("Categories", Unicode(255), nullable=False)
    # Per-session filter overrides (see schemas.match.BlindChatQueueRequest)
    # — MUST be persisted here, not just used one-shot at join time, because
    # this row is what a *later* joiner's own search finds and matches
    # against. NULL means "no override — use my profile defaults," checked
    # the same way on both sides of a pairing (see
    # blind_chat_service._compatibility_filters).
    gender_filter: Mapped[str | None] = mapped_column("GenderFilter", Unicode(10), nullable=True)
    min_age_filter: Mapped[int | None] = mapped_column("MinAgeFilter", Integer, nullable=True)
    max_age_filter: Mapped[int | None] = mapped_column("MaxAgeFilter", Integer, nullable=True)
    max_distance_km_filter: Mapped[int | None] = mapped_column("MaxDistanceKmFilter", Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
    # Set by whichever OTHER user's queue call claims this entry to pair with
    # it — the waiting side's own next GET/POST then sees this and reports
    # "matched" (deleting the row at that point). Deliberately NOT a
    # time-window heuristic ("matched within the last N minutes") — this
    # app process's clock and the DB server's real clock aren't guaranteed
    # to agree closely enough for a short window to be reliable, so
    # "matched" is discovered relationally instead. A row with this set is
    # also excluded from ever being matched against again (already claimed).
    # ON DELETE SET NULL, not the default NO ACTION — a Match can be deleted
    # out from under a still-lingering (matched-but-not-yet-observed) queue
    # entry, e.g. account.py's explicit `DELETE FROM Matches` on account
    # deletion; that must never fail with an FK violation. Losing the
    # match_id in that rare race just means the waiting side's next check
    # reports "waiting" instead of "matched" — safe, not a crash.
    matched_id: Mapped[uuid.UUID | None] = mapped_column(
        "MatchedId", ForeignKey("Matches.Id", ondelete="SET NULL"), nullable=True
    )
