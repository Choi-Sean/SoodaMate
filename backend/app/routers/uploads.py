from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.message import ImagePresignRequest
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


@router.post("/presign-chat-image", response_model=PresignResponse)
async def presign_chat_image(
    body: ImagePresignRequest, user: User = Depends(get_current_user)
) -> PresignResponse:
    """Images only (ImagePresignRequest's pattern rejects anything else) —
    used by the chat composer's image-send button. Separate from
    /presign (which still allows video, for profile media) since chat
    deliberately never supports video or arbitrary files."""
    object_path = storage_service.build_chat_image_object_path(user.id, body.content_type)
    upload_url = storage_service.generate_upload_url(object_path, body.content_type)
    return PresignResponse(upload_url=upload_url, gcs_object_path=object_path)


@router.post("/presign-story-image", response_model=PresignResponse)
async def presign_story_image(
    body: ImagePresignRequest, user: User = Depends(get_current_user)
) -> PresignResponse:
    """Images only, for the optional couple-story photo (routers/
    couple_stories.py) — same convention as presign-chat-image above."""
    object_path = storage_service.build_story_image_object_path(user.id, body.content_type)
    upload_url = storage_service.generate_upload_url(object_path, body.content_type)
    return PresignResponse(upload_url=upload_url, gcs_object_path=object_path)
