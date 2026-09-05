from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.match import MatchOut
from app.services.match_service import list_matches

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchOut])
async def get_matches(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[MatchOut]:
    return await list_matches(db, user.id)
