from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.device import DeviceRegisterRequest

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", status_code=204)
async def register_device(
    body: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await db.execute(
        text("EXEC sp_UpsertPushToken @UserId=:user_id, @FcmToken=:fcm_token, @Platform=:platform"),
        {"user_id": user.id, "fcm_token": body.fcm_token, "platform": body.platform},
    )
    await db.commit()
