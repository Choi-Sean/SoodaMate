from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.match import BlindChatQueueRequest, BlindChatQueueStatusOut
from app.services import blind_chat_service

router = APIRouter(prefix="/blind-chat", tags=["blind-chat"])


async def _require_complete_profile(db: AsyncSession, user: User) -> Profile:
    profile = await db.get(Profile, user.id)
    if profile is None or not profile.is_profile_complete:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    return profile


@router.post("/queue", response_model=BlindChatQueueStatusOut)
async def join_queue(
    body: BlindChatQueueRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlindChatQueueStatusOut:
    viewer_profile = await _require_complete_profile(db, user)
    return await blind_chat_service.join_queue(db, user, viewer_profile, body.categories)


@router.get("/queue", response_model=BlindChatQueueStatusOut)
async def queue_status(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> BlindChatQueueStatusOut:
    return await blind_chat_service.get_queue_status(db, user.id)


@router.delete("/queue", status_code=204)
async def leave_queue(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    await blind_chat_service.cancel_queue(db, user.id)
