import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Unicode, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Plain unique=True rejects a *second* NULL email on MSSQL (unlike
        # Postgres, which allows unlimited NULLs in a unique column) — a
        # filtered index only enforces uniqueness among non-NULL emails,
        # which is the actual intent (pure-OAuth users may share no email).
        Index("uq_users_email", "email", unique=True, mssql_where=text("email IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    auth_providers: Mapped[list["AuthProvider"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthProvider(Base):
    __tablename__ = "auth_providers"
    __table_args__ = (
        # Same NULL-uniqueness gotcha as above: every 'email' provider row
        # has provider_user_id=NULL, so a plain UNIQUE(provider,
        # provider_user_id) would reject the second email signup entirely on
        # MSSQL. Filtered index only enforces uniqueness for real (non-NULL)
        # OAuth provider_user_ids (google/kakao).
        Index(
            "uq_provider_identity",
            "provider",
            "provider_user_id",
            unique=True,
            mssql_where=text("provider_user_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(Unicode(20), nullable=False)  # 'google' | 'kakao' | 'email'
    provider_user_id: Mapped[str | None] = mapped_column(Unicode(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="auth_providers")
