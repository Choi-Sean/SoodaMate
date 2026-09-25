from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import rate_limit
from app.core.user_lock import user_lock
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
    # The app tells users identity verification is required before Blind Chat
    # and only checks that in its UI; enforce it here too so a direct API call
    # (or a modified client) can't skip it.
    if settings.require_verified_accounts and not profile.face_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "identity verification required")
    if profile.is_suspended:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account suspended")
    return profile


@router.post(
    "/queue",
    response_model=BlindChatQueueStatusOut,
    dependencies=[Depends(rate_limit.limit_user("blind_queue", 60, 600))],
)
async def join_queue(
    body: BlindChatQueueRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlindChatQueueStatusOut:
    # The lock comes BEFORE the profile read: a request that waited for another
    # of this user's requests must see that request's committed changes.
    async with user_lock(f"blind:{user.id}"):
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


@router.post("/ad-bonus", response_model=BlindChatLimitOut)
async def claim_ad_bonus(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> BlindChatLimitOut:
    return await blind_chat_service.claim_blind_chat_ad_bonus(db, user.id)


@router.post(
    "/ai-match", response_model=AiMatchOut, dependencies=[Depends(rate_limit.limit_user("ai_match", 30, 600))]
)
async def ai_match(
    body: AiMatchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiMatchOut:
    # Serialized per user (lock BEFORE reading the profile) so parallel calls
    # can't each see "1 credit left" and each spend it.
    async with user_lock(f"credits:{user.id}"):
        viewer_profile = await _require_complete_profile(db, user)
        match = await blind_chat_service.use_ai_match(
            db,
            user,
            viewer_profile,
            body.categories,
            body.gender,
            body.min_age,
            body.max_age,
            body.max_distance_km,
        )
    if match is None:
        return AiMatchOut(found=False)
    match_out = await match_service.get_match_out(db, match.id, user.id)
    return AiMatchOut(found=True, match=match_out)
