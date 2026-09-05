from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.verification import VerificationConfirmRequest, VerificationStartRequest
from app.services import verification_service
from app.services.email.smtp_sender import email_sender

router = APIRouter(prefix="/verification", tags=["verification"])


@router.post("/start", status_code=204)
async def start_verification(
    body: VerificationStartRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await verification_service.start_verification(db, email_sender, user.id, body.kind, body.email)


@router.post("/confirm", status_code=204)
async def confirm_verification(
    body: VerificationConfirmRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await verification_service.confirm_verification(db, user.id, body.kind, body.code)
