from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.match import SwipeLimitOut, SwipeRequest, SwipeResponse
from app.services.match_service import get_swipe_limit_status, record_swipe

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/swipe-limit", response_model=SwipeLimitOut)
async def swipe_limit(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeLimitOut:
    return await get_swipe_limit_status(db, user.id)


@router.post("/like", response_model=SwipeResponse)
async def like(
    body: SwipeRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeResponse:
    return await record_swipe(db, user.id, body.to_user_id, "like")


@router.post("/pass", response_model=SwipeResponse)
async def pass_(
    body: SwipeRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeResponse:
    return await record_swipe(db, user.id, body.to_user_id, "pass")


@router.post("/superlike", response_model=SwipeResponse)
async def superlike(
    body: SwipeRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeResponse:
    return await record_swipe(db, user.id, body.to_user_id, "superlike")
