from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.core.user_lock import user_lock
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.match import SwipeLimitOut, SwipeRequest, SwipeResponse
from app.services.match_service import claim_swipe_ad_bonus, get_swipe_limit_status, record_swipe

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/swipe-limit", response_model=SwipeLimitOut)
async def swipe_limit(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeLimitOut:
    return await get_swipe_limit_status(db, user.id)


@router.post("/swipe-limit/ad-bonus", response_model=SwipeLimitOut)
async def claim_swipe_bonus(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeLimitOut:
    return await claim_swipe_ad_bonus(db, user.id)


@router.post("/like", response_model=SwipeResponse, dependencies=[Depends(rate_limit.limit_user("swipe", 600, 600))])
async def like(
    body: SwipeRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeResponse:
    async with user_lock(f"swipe:{user.id}"):
        return await record_swipe(db, user.id, body.to_user_id, "like")


@router.post("/pass", response_model=SwipeResponse, dependencies=[Depends(rate_limit.limit_user("swipe", 600, 600))])
async def pass_(
    body: SwipeRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeResponse:
    async with user_lock(f"swipe:{user.id}"):
        return await record_swipe(db, user.id, body.to_user_id, "pass")


@router.post("/superlike", response_model=SwipeResponse, dependencies=[Depends(rate_limit.limit_user("swipe", 600, 600))])
async def superlike(
    body: SwipeRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeResponse:
    # Lock order is always swipe -> credits, so this can never deadlock against
    # a webhook grant (which only takes the credits lock).
    async with user_lock(f"swipe:{user.id}"), user_lock(f"credits:{user.id}"):
        return await record_swipe(db, user.id, body.to_user_id, "superlike")
