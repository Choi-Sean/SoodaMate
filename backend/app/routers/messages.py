import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.database import get_db
from app.deps import get_current_user
from app.models.message import Message
from app.models.user import User
from app.schemas.message import MessageOut, TranslateMessageOut, TranslateMessageRequest
from app.services import chat_service, translation_service

router = APIRouter(prefix="/matches", tags=["messages"])


@router.get("/{match_id}/messages", response_model=list[MessageOut])
async def get_messages(
    match_id: uuid.UUID,
    before: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MessageOut]:
    # get_match_for_user, not get_active_match_for_user — an expired
    # match's past messages stay readable, only sending into it is blocked.
    match = await chat_service.get_match_for_user(db, match_id, user.id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")
    return await chat_service.get_history(db, match_id, before, limit)


@router.post(
    "/{match_id}/messages/{message_id}/translate",
    response_model=TranslateMessageOut,
    dependencies=[Depends(rate_limit.limit_user("translate", 60, 600))],
)
async def translate_message(
    match_id: uuid.UUID,
    message_id: uuid.UUID,
    body: TranslateMessageRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TranslateMessageOut:
    """On-demand translate, distinct from the automatic translation ws_chat.py
    attaches at send time (that one only ever targets the recipient's saved
    preferred_language). This lets either side translate any message — including
    their own, and into any of the 5 app languages, not just their default —
    the same reason a picker exists at all here."""
    match = await chat_service.get_match_for_user(db, match_id, user.id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")

    message = await db.get(Message, message_id)
    if message is None or message.match_id != match_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
    if message.message_type != "text":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "only text messages can be translated")

    # No source_lang: Google auto-detects it. message.original_language is only ever
    # set for the auto-translate-at-send-time path and is usually None, and passing a
    # wrong/stale source would just as likely misfire the "same as target -> skip" guard.
    translated = await translation_service.translate(message.content, body.target_language)
    if translated is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "translation is unavailable right now")
    return TranslateMessageOut(translated_content=translated, target_language=body.target_language)
