import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Unicode, UnicodeText, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Swipe(Base):
    __tablename__ = "Swipes"
    __table_args__ = (UniqueConstraint("FromUserId", "ToUserId", name="uq_swipe_pair"),)

    # No ondelete=CASCADE here: MSSQL rejects two CASCADE paths from the same
    # table to the same target (from_user_id + to_user_id both -> users)
    # as an ambiguous multi-cascade-path. account.py deletes swipes/matches/
    # blocks/reports rows explicitly before deleting the user row instead.
    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id: Mapped[uuid.UUID] = mapped_column("FromUserId", ForeignKey("Users.Id"), nullable=False)
    to_user_id: Mapped[uuid.UUID] = mapped_column("ToUserId", ForeignKey("Users.Id"), nullable=False)
    action: Mapped[str] = mapped_column("Action", Unicode(10), nullable=False)  # 'like' | 'pass' | 'superlike'
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())


class Match(Base):
    __tablename__ = "Matches"
    __table_args__ = (UniqueConstraint("UserAId", "UserBId", name="uq_match_pair"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_a_id: Mapped[uuid.UUID] = mapped_column("UserAId", ForeignKey("Users.Id"), nullable=False)
    user_b_id: Mapped[uuid.UUID] = mapped_column("UserBId", ForeignKey("Users.Id"), nullable=False)
    matched_at: Mapped[datetime] = mapped_column("MatchedAt", DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column("IsActive", Boolean, default=True, nullable=False)

    # Phase 14 — Bumble-style first-message rule. Snapshotted at match-creation
    # time (not derived live from current profile gender) so an edited gender
    # never retroactively changes an already-formed match's rule. NULL means
    # unrestricted (same-gender or either profile is 'other') — open messaging
    # immediately, matching Bumble's real BFF/same-sex behavior.
    restricted_to_user_id: Mapped[uuid.UUID | None] = mapped_column(
        "RestrictedToUserId", ForeignKey("Users.Id"), nullable=True
    )
    first_message_deadline: Mapped[datetime | None] = mapped_column(
        "FirstMessageDeadline", DateTime(timezone=True), nullable=True
    )
    first_message_sent: Mapped[bool] = mapped_column("FirstMessageSent", Boolean, default=False, nullable=False)

    # Generalizes the same 24h-no-reply expiry beyond just "the first
    # message never got sent": once a conversation is underway, it goes
    # stale (is_active flips False) if 24h pass with nobody replying to
    # the most recent message, whoever sent it. NULL until the first
    # message; chat_service falls back to matched_at for rows written
    # before this column existed.
    last_activity_at: Mapped[datetime | None] = mapped_column(
        "LastActivityAt", DateTime(timezone=True), nullable=True
    )

    # Blind chat (category-based random 1:1) — see services/blind_chat_service.py.
    # False/NULL for every ordinary swipe-created match; a blind match starts
    # unrestricted (restricted_to_user_id stays NULL — either side can just
    # start talking, no Bumble-style first-message gate) but the OTHER
    # person's name/photo stay masked in MatchOut until blind_revealed flips.
    is_blind: Mapped[bool] = mapped_column("IsBlind", Boolean, default=False, nullable=False)
    # Comma-separated — the categories both sides' queue selections had in
    # common at pairing time, shown to explain "why you were matched".
    blind_categories: Mapped[str | None] = mapped_column("BlindCategories", Unicode(255), nullable=True)
    blind_revealed: Mapped[bool] = mapped_column("BlindRevealed", Boolean, default=False, nullable=False)
    # Snapshotted at match-creation time, same convention as
    # restricted_to_user_id above: for a male/female pair this is the female
    # user's id (only she may propose revealing profiles — mirrors the
    # existing first-message rule's reasoning, she stays in control of when
    # anonymity ends); NULL means either side may propose (same-gender or
    # "other" pairs — an interim default, see the
    # soodamate-blind-chat-open-decisions memory note for the follow-up).
    blind_reveal_eligible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        "BlindRevealEligibleUserId", ForeignKey("Users.Id"), nullable=True
    )
    # Who has an outstanding "reveal profiles" request pending the other
    # side's accept, if anyone. Left set (not cleared) after an accept —
    # harmless once blind_revealed is True, and keeps a record of who asked.
    blind_reveal_requested_by: Mapped[uuid.UUID | None] = mapped_column(
        "BlindRevealRequestedBy", ForeignKey("Users.Id"), nullable=True
    )


class Block(Base):
    __tablename__ = "Blocks"
    __table_args__ = (UniqueConstraint("BlockerId", "BlockedId", name="uq_block_pair"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id: Mapped[uuid.UUID] = mapped_column("BlockerId", ForeignKey("Users.Id"), nullable=False)
    blocked_id: Mapped[uuid.UUID] = mapped_column("BlockedId", ForeignKey("Users.Id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "Reports"

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column("ReporterId", ForeignKey("Users.Id"), nullable=False)
    reported_id: Mapped[uuid.UUID] = mapped_column("ReportedId", ForeignKey("Users.Id"), nullable=False)
    reason: Mapped[str] = mapped_column("Reason", Unicode(100), nullable=False)
    detail: Mapped[str | None] = mapped_column("Detail", UnicodeText, nullable=True)
    status: Mapped[str] = mapped_column("Status", Unicode(20), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
