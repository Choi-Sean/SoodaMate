from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.database import get_db
from app.services import ad_ssv_service

router = APIRouter(prefix="/ads", tags=["ads"])


@router.get("/ssv", dependencies=[Depends(rate_limit.limit_ip("ads_ssv", 600, 600))])
async def rewarded_ad_callback(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Called by Google (not by the app) after a rewarded ad completes. The raw
    query string is what Google signed, so it is passed through untouched."""
    await ad_ssv_service.verify_and_grant(db, request.scope["query_string"].decode())
    return {"status": "ok"}
