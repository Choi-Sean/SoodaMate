import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.message import MessageOut
from app.services import chat_service

router = APIRouter(prefix="/matches", tags=["messages"])


@router.get("/{match_id}/messages", response_model=list[MessageOut])
async def get_messages(
    match_id: uuid.UUID,
    before: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MessageOut]:
    match = await chat_service.get_active_match_for_user(db, match_id, user.id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")
    return await chat_service.get_history(db, match_id, before, limit)
