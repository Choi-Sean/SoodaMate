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
