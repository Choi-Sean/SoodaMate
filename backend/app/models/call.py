import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Unicode, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CallSession(Base):
    __tablename__ = "CallSessions"

    # caller_id/callee_id have no ondelete=CASCADE — same MSSQL multi-cascade-
    # path restriction as Swipe/Match/Block/Report (see interaction.py).
    # match_id can stay CASCADE: it's the only path from call_sessions to
    # matches, no ambiguity.
    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(
        "MatchId", ForeignKey("Matches.Id", ondelete="CASCADE"), nullable=False
    )
    caller_id: Mapped[uuid.UUID] = mapped_column("CallerId", ForeignKey("Users.Id"), nullable=False)
    callee_id: Mapped[uuid.UUID] = mapped_column("CalleeId", ForeignKey("Users.Id"), nullable=False)
    status: Mapped[str] = mapped_column("Status", Unicode(20), default="ringing", nullable=False)
    # 'ringing' | 'active' | 'ended' | 'declined' | 'missed'
    end_reason: Mapped[str | None] = mapped_column("EndReason", Unicode(20), nullable=True)
    # 'hangup' | 'declined' | 'cancelled' | 'timeout' | 'peer_offline'
    started_at: Mapped[datetime] = mapped_column("StartedAt", DateTime(timezone=True), server_default=func.now())
    connected_at: Mapped[datetime | None] = mapped_column("ConnectedAt", DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column("EndedAt", DateTime(timezone=True), nullable=True)
