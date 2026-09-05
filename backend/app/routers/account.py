from fastapi import APIRouter, Depends
from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.interaction import Block, Match, Report, Swipe
from app.models.user import User

router = APIRouter(prefix="/account", tags=["account"])


@router.delete("/me", status_code=204)
async def delete_my_account(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    # Swipe/Match/Block/Report have no ondelete=CASCADE back to users (MSSQL
    # rejects two CASCADE paths to the same table from one row) — deleted
    # explicitly here, in this order, before the user row. Matches must go
    # before the user delete since Match.restricted_to_user_id also points at
    # users; deleting matches first also cascades to messages/call_sessions
    # (those two DO still cascade from matches.id, a single unambiguous path).
    # Everything else (profiles, photos, auth_providers, push_tokens,
    # verifications, iap_transactions) still cascades from the user delete.
    await db.execute(delete(Swipe).where(or_(Swipe.from_user_id == user.id, Swipe.to_user_id == user.id)))
    await db.execute(delete(Match).where(or_(Match.user_a_id == user.id, Match.user_b_id == user.id)))
    await db.execute(delete(Block).where(or_(Block.blocker_id == user.id, Block.blocked_id == user.id)))
    await db.execute(delete(Report).where(or_(Report.reporter_id == user.id, Report.reported_id == user.id)))
    await db.delete(user)
    await db.commit()
