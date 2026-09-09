import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CoupleStory(Base):
    """A "we matched here" success story, submitted by one matched user and
    requiring the other (peer_id) to confirm before it's visible to anyone
    but the two of them — see services/couple_story_service.py. One story
    per match (uq constraint on match_id): re-submitting isn't supported in
    v1, the author just waits for peer_id to confirm/decline the first one.

    author_id/peer_id point at Users without ondelete=CASCADE (same reason
    as Swipe.from_user_id/to_user_id — MSSQL rejects two CASCADE paths to
    the same table). This is harmless in practice: deleting an account
    always deletes that user's Matches first (routers/account.py), which
    cascades match_id -> this table already, so by the time the user row
    itself is deleted every CoupleStory referencing them (as author or
    peer) is already gone."""

    __tablename__ = "CoupleStories"
    __table_args__ = (UniqueConstraint("MatchId", name="uq_couple_story_match"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id: Mapped[uuid.UUID] = mapped_column(
        "MatchId", ForeignKey("Matches.Id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column("AuthorId", ForeignKey("Users.Id"), nullable=False)
    peer_id: Mapped[uuid.UUID] = mapped_column("PeerId", ForeignKey("Users.Id"), nullable=False)
    story_text: Mapped[str] = mapped_column("StoryText", UnicodeText, nullable=False)
    # Optional couple photo — never the individual dating-profile photos
    # (the public feed deliberately never surfaces those; see
    # routers/couple_stories.py). Same image-only presign convention as
    # chat images (build_story_image_object_path), under users/{id}/stories/.
    photo_object_path: Mapped[str | None] = mapped_column("PhotoObjectPath", Unicode(512), nullable=True)
    # "pending" (waiting on peer_id) | "published" | "declined" | "hidden"
    # (auto-hidden past the report threshold — see couple_story_service.
    # REPORT_HIDE_THRESHOLD; no moderation queue UI exists yet, same
    # documented gap as FaceVerification's manual review page).
    status: Mapped[str] = mapped_column("Status", Unicode(20), nullable=False, default="pending")
    report_count: Mapped[int] = mapped_column("ReportCount", Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
    published_at: Mapped[datetime | None] = mapped_column("PublishedAt", DateTime(timezone=True), nullable=True)


class CoupleStoryReport(Base):
    __tablename__ = "CoupleStoryReports"
    __table_args__ = (UniqueConstraint("StoryId", "ReporterId", name="uq_couple_story_report"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(
        "StoryId", ForeignKey("CoupleStories.Id", ondelete="CASCADE"), nullable=False
    )
    # No ondelete=CASCADE (same reasoning as CoupleStory.author_id/peer_id
    # above) — routers/account.py deletes a departing user's own filed
    # reports explicitly, since those aren't otherwise reachable via any
    # cascade off that user's own matches.
    reporter_id: Mapped[uuid.UUID] = mapped_column("ReporterId", ForeignKey("Users.Id"), nullable=False)
    reason: Mapped[str] = mapped_column("Reason", Unicode(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
