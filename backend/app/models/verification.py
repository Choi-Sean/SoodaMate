import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Verification(Base):
    __tablename__ = "Verifications"
    __table_args__ = (UniqueConstraint("UserId", "Kind", name="uq_verification_user_kind"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column("Kind", Unicode(10), nullable=False)  # 'work' | 'school'
    email: Mapped[str] = mapped_column("Email", Unicode(255), nullable=False)
    domain: Mapped[str] = mapped_column("Domain", Unicode(255), nullable=False)
    code_hash: Mapped[str] = mapped_column("CodeHash", Unicode(255), nullable=False)
    attempts: Mapped[int] = mapped_column("Attempts", Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column("ExpiresAt", DateTime(timezone=True), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column("VerifiedAt", DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
