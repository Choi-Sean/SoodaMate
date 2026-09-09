import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Unicode, UnicodeText, Uuid, func
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
    # "" for an image message (no caption support in v1) — kept NOT NULL
    # rather than nullable so every existing read site that treats content
    # as a plain string keeps working unchanged.
    content: Mapped[str] = mapped_column("Content", UnicodeText, nullable=False)
    # "text" | "image" — image messages carry image_object_path instead of
    # meaningful content. server_default backfills existing rows as "text".
    message_type: Mapped[str] = mapped_column(
        "MessageType", Unicode(10), nullable=False, server_default="text", default="text"
    )
    # R2 object path for an image message — same public-bucket/unguessable-
    # UUID-path convention as Photo.gcs_object_path, under users/{id}/chat/.
    # Only images are accepted (see storage_service.build_chat_image_object_path
    # + schemas/message.py's ImagePresignRequest) — never video, never an
    # arbitrary file.
    image_object_path: Mapped[str | None] = mapped_column("ImageObjectPath", Unicode(512), nullable=True)
    # Real-time translation (services/translation_service.py). Only ever set
    # for text messages where the sender's and recipient's preferred_language
    # differ and translation is configured — see routers/ws_chat.py. NULL
    # translated_content means "no translation available/needed", not an
    # error; the client always still has the original `content` to show.
    original_language: Mapped[str | None] = mapped_column("OriginalLanguage", Unicode(10), nullable=True)
    translated_content: Mapped[str | None] = mapped_column("TranslatedContent", UnicodeText, nullable=True)
    translated_language: Mapped[str | None] = mapped_column("TranslatedLanguage", Unicode(10), nullable=True)
    sent_at: Mapped[datetime] = mapped_column("SentAt", DateTime(timezone=True), server_default=func.now())
    delivered_at: Mapped[datetime | None] = mapped_column("DeliveredAt", DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column("ReadAt", DateTime(timezone=True), nullable=True)
