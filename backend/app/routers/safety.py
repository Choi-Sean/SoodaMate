from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.database import get_db
from app.deps import get_current_user
from app.models.interaction import Match, Report
from app.models.user import User
from app.schemas.safety import BlockRequest, ReportRequest
from app.utils.db_retry import run_with_deadlock_retry

router = APIRouter(prefix="/safety", tags=["safety"])


@router.post("/block", status_code=204, dependencies=[Depends(rate_limit.limit_user("block", 60, 3600))])
async def block_user(
    body: BlockRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    if body.user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot block yourself")
    # The target's card could have been fetched a while before this request
    # lands (a full discovery deck stays cached client-side) — if the
    # account was deleted in between, a plain INSERT/EXEC would otherwise
    # 500 on the FK constraint instead of a clean, expected 404.
    target = await db.get(User, body.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    async def _block_transaction() -> None:
        await db.execute(
            text("EXEC sp_UpsertBlock @BlockerId=:blocker_id, @BlockedId=:blocked_id"),
            {"blocker_id": user.id, "blocked_id": body.user_id},
        )
        # Blocking must also end any conversation that already exists between the
        # two — otherwise the blocked person could keep messaging (or calling)
        # through the old match. chat_service only lets people send into active
        # matches, so deactivating is enough; list_matches hides blocked pairs.
        await db.execute(
            update(Match)
            .where(
                or_(
                    and_(Match.user_a_id == user.id, Match.user_b_id == body.user_id),
                    and_(Match.user_a_id == body.user_id, Match.user_b_id == user.id),
                ),
                Match.is_active,
            )
            .values(is_active=False)
        )
        await db.commit()

    # Can deadlock against a concurrent swipe between the same two people (SQL
    # Server kills one side, error 1205); redoing the transaction is the fix.
    await run_with_deadlock_retry(db, _block_transaction)


@router.post("/report", status_code=204, dependencies=[Depends(rate_limit.limit_user("report", 20, 3600))])
async def report_user(
    body: ReportRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    if body.user_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot report yourself")
    # Same stale-card race as block_user above.
    target = await db.get(User, body.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    db.add(
        Report(reporter_id=user.id, reported_id=body.user_id, reason=body.reason, detail=body.detail)
    )
    await db.commit()
