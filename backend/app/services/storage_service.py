import uuid

import boto3
from botocore.config import Config

from app.config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            # R2 speaks the S3 API but isn't region-partitioned like AWS —
            # "auto" is Cloudflare's documented region value for the S3 client.
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )
    return _client


_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "video/mp4": "mp4"}


def build_object_path(user_id: uuid.UUID, content_type: str) -> str:
    ext = _EXTENSIONS[content_type]
    return f"users/{user_id}/photos/{uuid.uuid4()}.{ext}"


def media_type_from_object_path(object_path: str) -> str:
    """Derived server-side from the extension build_object_path gave the
    upload, never trusted from client input — routers/profiles.py::
    confirm_photo uses this to set Photo.media_type."""
    return "video" if object_path.lower().endswith(".mp4") else "photo"


def generate_upload_url(object_path: str, content_type: str) -> str:
    # ContentType is bound into the signature, so the client's PUT must send
    # the exact same Content-Type header or R2 rejects it with a signature
    # mismatch — same contract the old GCS signed URL had.
    return _get_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": object_path, "ContentType": content_type},
        ExpiresIn=15 * 60,
    )


def build_public_url(object_path: str) -> str:
    """Bucket is public-read (R2.dev subdomain or a mapped custom domain)
    with non-guessable UUID paths — no signed GET needed, same as before."""
    return f"{settings.r2_public_url}/{object_path}"
