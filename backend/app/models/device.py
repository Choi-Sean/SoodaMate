import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Unicode, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PushToken(Base):
    __tablename__ = "PushTokens"
    __table_args__ = (UniqueConstraint("FcmToken", name="uq_fcm_token"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    fcm_token: Mapped[str] = mapped_column("FcmToken", Unicode(255), nullable=False)
    platform: Mapped[str] = mapped_column("Platform", Unicode(10), nullable=False)  # 'ios' | 'android'
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
