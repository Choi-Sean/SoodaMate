from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.match import (
    AiMatchOut,
    AiMatchRequest,
    BlindChatLimitOut,
    BlindChatQueueRequest,
    BlindChatQueueStatusOut,
)
from app.services import blind_chat_service, match_service

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
    return await blind_chat_service.join_queue(
        db, user, viewer_profile, body.categories, body.gender, body.min_age, body.max_age, body.max_distance_km
    )


@router.get("/queue", response_model=BlindChatQueueStatusOut)
async def queue_status(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> BlindChatQueueStatusOut:
    return await blind_chat_service.get_queue_status(db, user.id)


@router.delete("/queue", status_code=204)
async def leave_queue(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> None:
    await blind_chat_service.cancel_queue(db, user.id)


@router.get("/limit", response_model=BlindChatLimitOut)
async def get_limit(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> BlindChatLimitOut:
    return await blind_chat_service.get_blind_chat_limit_status(db, user.id)


@router.post("/ai-match", response_model=AiMatchOut)
async def ai_match(
    body: AiMatchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiMatchOut:
    viewer_profile = await _require_complete_profile(db, user)
    match = await blind_chat_service.use_ai_match(db, user, viewer_profile, body.categories)
    if match is None:
        return AiMatchOut(found=False)
    match_out = await match_service.get_match_out(db, match.id, user.id)
    return AiMatchOut(found=True, match=match_out)
