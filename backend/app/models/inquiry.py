import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Unicode, UnicodeText, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContactInquiry(Base):
    """A user's 1:1 문의/건의 (contact/feedback) submission, reviewed from the
    admin dashboard. 'new' inquiries drive the unread-badge there; resolving
    one is a one-way admin action (no reply channel back to the user in v1 —
    see docs/ARCHITECTURE.md if that's ever added)."""

    __tablename__ = "ContactInquiries"

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    subject: Mapped[str] = mapped_column("Subject", Unicode(200), nullable=False)
    message: Mapped[str] = mapped_column("Message", UnicodeText, nullable=False)
    status: Mapped[str] = mapped_column("Status", Unicode(20), default="new", nullable=False)  # 'new' | 'read' | 'resolved'
    admin_note: Mapped[str | None] = mapped_column("AdminNote", UnicodeText, nullable=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column("ResolvedAt", DateTime(timezone=True), nullable=True)
