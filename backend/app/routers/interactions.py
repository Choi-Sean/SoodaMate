from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.core.user_lock import user_lock
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


# Like/Super Like discontinued: Classic Matching's swipe/discovery UI has no
# reachable entry point anywhere in the app anymore (see MyProfileScreen.tsx's
# comment on why those link cards were removed) — nobody can ever hit these,
# so they're discontinued outright rather than left live-but-unreachable.
# match_service.record_swipe still accepts "like"/"superlike" as actions (the
# stored proc and match-creation semantics are unchanged internally, and
# tests still exercise it directly — see tests/helpers.create_ordinary_match)
# — it's only this public HTTP surface that's closed off. /pass stays open:
# it's still the free-tier swipe-limit's own subject (GET /interactions/
# swipe-limit) and has no monetization/notification baggage to discontinue.
_DISCONTINUED_DETAIL = "Classic Matching's Like/Super Like has been discontinued"


@router.post("/like", include_in_schema=False)
async def like() -> None:
    raise HTTPException(status.HTTP_410_GONE, _DISCONTINUED_DETAIL)


@router.post("/pass", response_model=SwipeResponse, dependencies=[Depends(rate_limit.limit_user("swipe", 600, 600))])
async def pass_(
    body: SwipeRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> SwipeResponse:
    async with user_lock(f"swipe:{user.id}"):
        return await record_swipe(db, user.id, body.to_user_id, "pass")


@router.post("/superlike", include_in_schema=False)
async def superlike() -> None:
    raise HTTPException(status.HTTP_410_GONE, _DISCONTINUED_DETAIL)
