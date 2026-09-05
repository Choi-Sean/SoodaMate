import uuid
from datetime import timedelta

from google.cloud import storage

from app.config import settings

_client: storage.Client | None = None


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def build_object_path(user_id: uuid.UUID, content_type: str) -> str:
    ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
    return f"users/{user_id}/photos/{uuid.uuid4()}.{ext}"


def generate_upload_url(object_path: str, content_type: str) -> str:
    bucket = _get_client().bucket(settings.gcs_bucket_name)
    blob = bucket.blob(object_path)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="PUT",
        content_type=content_type,
    )
