import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UnicodeText, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Message(Base):
    __tablename__ = "Messages"
    __table_args__ = (Index("ix_messages_match_sent", "MatchId", "SentAt"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(
        "MatchId", ForeignKey("Matches.Id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        "SenderId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column("Content", UnicodeText, nullable=False)
    sent_at: Mapped[datetime] = mapped_column("SentAt", DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column("DeliveredAt", DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column("ReadAt", DateTime(timezone=True), nullable=True)
