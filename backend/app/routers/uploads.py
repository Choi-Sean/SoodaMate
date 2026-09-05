from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.profile import PresignRequest, PresignResponse
from app.services import storage_service

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(
    body: PresignRequest, user: User = Depends(get_current_user)
) -> PresignResponse:
    object_path = storage_service.build_object_path(user.id, body.content_type)
    upload_url = storage_service.generate_upload_url(object_path, body.content_type)
    return PresignResponse(upload_url=upload_url, gcs_object_path=object_path)
