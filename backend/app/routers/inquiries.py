from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.inquiry import ContactInquiry
from app.models.user import User
from app.schemas.inquiry import InquiryCreateRequest

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.post("", status_code=204)
async def create_inquiry(
    body: InquiryCreateRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    db.add(ContactInquiry(user_id=user.id, subject=body.subject, message=body.message))
    await db.commit()
