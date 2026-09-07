from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import FaceVerification
from app.models.user import User
from app.schemas.verification import (
    FacePresignRequest,
    FaceVerificationStatusOut,
    VerificationConfirmRequest,
    VerificationStartRequest,
)
from app.services import storage_service, verification_service
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


@router.post("/face/presign")
async def presign_face_photo(
    body: FacePresignRequest,
    user: User = Depends(get_current_user),
) -> dict:
    object_path = storage_service.build_face_verification_object_path(user.id, body.content_type)
    return {
        "upload_url": storage_service.generate_upload_url(object_path, body.content_type),
        "gcs_object_path": object_path,
    }


@router.post("/face/submit", response_model=FaceVerificationStatusOut, status_code=201)
async def submit_face_verification(
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FaceVerification:
    object_path = body.get("gcs_object_path")
    if not object_path or not object_path.startswith(f"verifications/{user.id}/"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or missing gcs_object_path")

    # A fresh submission always resets to pending, including re-submitting
    # after a rejection — one row per user, not an accumulating history.
    existing = await db.scalar(select(FaceVerification).where(FaceVerification.user_id == user.id))
    if existing is not None:
        existing.gcs_object_path = object_path
        existing.status = "pending"
        existing.reviewed_at = None
        row = existing
    else:
        row = FaceVerification(user_id=user.id, gcs_object_path=object_path, status="pending")
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("/face/status", response_model=FaceVerificationStatusOut)
async def get_face_verification_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FaceVerification | FaceVerificationStatusOut:
    row = await db.scalar(select(FaceVerification).where(FaceVerification.user_id == user.id))
    if row is None:
        return FaceVerificationStatusOut(status="unsubmitted")
    return row
