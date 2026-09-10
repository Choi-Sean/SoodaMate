import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Unicode, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Moment(Base):
    """A "요즘 나 / Lately" item — one photo + an optional short caption,
    dated. Deliberately NOT a social feed: no likes, comments, ranking, or
    notifications. A rolling window of the newest MOMENT_LIMIT per user
    (older ones are pruned on insert — see moment_service.create_moment),
    shown on the profile the same way profile photos are (own MyProfile,
    and other users' candidate cards).

    Single FK to Users with ondelete=CASCADE — no ambiguous multi-path
    problem here (unlike Swipe/Match), so a user delete cleans these up
    automatically, no explicit routers/account.py handling needed."""

    __tablename__ = "Moments"
    __table_args__ = (Index("ix_moments_user_created", "UserId", "CreatedAt"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    image_object_path: Mapped[str] = mapped_column("ImageObjectPath", Unicode(512), nullable=False)
    caption: Mapped[str | None] = mapped_column("Caption", Unicode(280), nullable=True)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
