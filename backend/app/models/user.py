import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Unicode, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "Users"
    __table_args__ = (
        # Plain unique=True rejects a *second* NULL email on MSSQL (unlike
        # Postgres, which allows unlimited NULLs in a unique column) — a
        # filtered index only enforces uniqueness among non-NULL emails,
        # which is the actual intent (pure-OAuth users may share no email).
        Index("uq_users_email", "Email", unique=True, mssql_where=text("Email IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column("Email", Unicode(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column("PasswordHash", Unicode(255), nullable=True)
    is_active: Mapped[bool] = mapped_column("IsActive", Boolean, default=True, nullable=False)
    is_banned: Mapped[bool] = mapped_column("IsBanned", Boolean, default=False, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        "LastActiveAt", DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        "UpdatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    auth_providers: Mapped[list["AuthProvider"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthProvider(Base):
    __tablename__ = "AuthProviders"
    __table_args__ = (
        # Same NULL-uniqueness gotcha as above: every 'email' provider row
        # has provider_user_id=NULL, so a plain UNIQUE(provider,
        # provider_user_id) would reject the second email signup entirely on
        # MSSQL. Filtered index only enforces uniqueness for real (non-NULL)
        # OAuth provider_user_ids (google/kakao).
        Index(
            "uq_provider_identity",
            "Provider",
            "ProviderUserId",
            unique=True,
            mssql_where=text("ProviderUserId IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column("Provider", Unicode(20), nullable=False)  # 'google' | 'kakao' | 'email'
    provider_user_id: Mapped[str | None] = mapped_column("ProviderUserId", Unicode(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="auth_providers")
