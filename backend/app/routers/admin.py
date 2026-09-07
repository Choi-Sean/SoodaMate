from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models.profile import FaceVerification, Profile
from app.models.user import User
from app.schemas.verification import FaceVerificationAdminOut, FaceVerificationRejectRequest

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/face-verifications", response_model=list[FaceVerificationAdminOut])
async def list_face_verifications(
    status_filter: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|all)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[FaceVerificationAdminOut]:
    stmt = select(FaceVerification, Profile.display_name).join(
        Profile, Profile.user_id == FaceVerification.user_id, isouter=True
    )
    if status_filter != "all":
        stmt = stmt.where(FaceVerification.status == status_filter)
    stmt = stmt.order_by(FaceVerification.submitted_at.desc())

    rows = (await db.execute(stmt)).all()
    out = []
    for verification, display_name in rows:
        item = FaceVerificationAdminOut.model_validate(verification)
        item.display_name = display_name
        out.append(item)
    return out


async def _get_verification_or_404(db: AsyncSession, verification_id) -> FaceVerification:
    row = await db.get(FaceVerification, verification_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "verification not found")
    return row


@router.post("/face-verifications/{verification_id}/approve", status_code=204)
async def approve_face_verification(
    verification_id,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    from datetime import datetime, timezone

    verification = await _get_verification_or_404(db, verification_id)
    verification.status = "approved"
    verification.reviewed_at = datetime.now(timezone.utc)
    verification.rejection_reason = None
    verification.rejection_reason_key = None
    profile = await db.get(Profile, verification.user_id)
    if profile is not None:
        profile.face_verified = True
    await db.commit()


@router.post("/face-verifications/{verification_id}/reject", status_code=204)
async def reject_face_verification(
    verification_id,
    body: FaceVerificationRejectRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    from datetime import datetime, timezone

    verification = await _get_verification_or_404(db, verification_id)
    verification.status = "rejected"
    verification.reviewed_at = datetime.now(timezone.utc)
    verification.rejection_reason = body.reason
    verification.rejection_reason_key = body.reason_key
    profile = await db.get(Profile, verification.user_id)
    if profile is not None:
        profile.face_verified = False
    await db.commit()
