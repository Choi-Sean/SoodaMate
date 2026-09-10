import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.moment import MomentCreate, MomentOut
from app.services import moment_service

router = APIRouter(prefix="/moments", tags=["moments"])


@router.get("/me", response_model=list[MomentOut])
async def my_moments(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[MomentOut]:
    return await moment_service.list_moments(db, user.id)


@router.post("", response_model=MomentOut, status_code=201)
async def create_moment(
    body: MomentCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> MomentOut:
    return await moment_service.create_moment(db, user.id, body.image_object_path, body.caption)


@router.delete("/{moment_id}", status_code=204)
async def delete_moment(
    moment_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    ok = await moment_service.delete_moment(db, moment_id, user.id)
    if not ok:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "moment not found")
