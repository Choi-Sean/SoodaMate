from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.interaction import Report
from app.models.user import User
from app.schemas.safety import BlockRequest, ReportRequest

router = APIRouter(prefix="/safety", tags=["safety"])


@router.post("/block", status_code=204)
async def block_user(
    body: BlockRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    if body.user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot block yourself")
    await db.execute(
        text("EXEC sp_UpsertBlock @BlockerId=:blocker_id, @BlockedId=:blocked_id"),
        {"blocker_id": user.id, "blocked_id": body.user_id},
    )
    await db.commit()


@router.post("/report", status_code=204)
async def report_user(
    body: ReportRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    if body.user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot report yourself")
    db.add(
        Report(reporter_id=user.id, reported_id=body.user_id, reason=body.reason, detail=body.detail)
    )
    await db.commit()
