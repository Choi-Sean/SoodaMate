import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Unicode, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PushToken(Base):
    __tablename__ = "push_tokens"
    __table_args__ = (UniqueConstraint("fcm_token", name="uq_fcm_token"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fcm_token: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    platform: Mapped[str] = mapped_column(Unicode(10), nullable=False)  # 'ios' | 'android'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
