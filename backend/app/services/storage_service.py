import re
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

# Images only (no video, no arbitrary files) — deliberately a separate,
# narrower map from _EXTENSIONS above, enforced by schemas.message.
# ImagePresignRequest's pattern validator before either path builder below
# is ever called.
_IMAGE_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


def build_object_path(user_id: uuid.UUID, content_type: str) -> str:
    ext = _EXTENSIONS[content_type]
    return f"users/{user_id}/photos/{uuid.uuid4()}.{ext}"


def build_chat_image_object_path(user_id: uuid.UUID, content_type: str) -> str:
    ext = _IMAGE_EXTENSIONS[content_type]
    return f"users/{user_id}/chat/{uuid.uuid4()}.{ext}"


def build_story_image_object_path(user_id: uuid.UUID, content_type: str) -> str:
    ext = _IMAGE_EXTENSIONS[content_type]
    return f"users/{user_id}/stories/{uuid.uuid4()}.{ext}"


def build_moment_image_object_path(user_id: uuid.UUID, content_type: str) -> str:
    ext = _IMAGE_EXTENSIONS[content_type]
    return f"users/{user_id}/moments/{uuid.uuid4()}.{ext}"


def build_face_verification_object_path(user_id: uuid.UUID, content_type: str, kind: str = "selfie") -> str:
    # A random, unguessable path. With settings.r2_private_bucket_name set it
    # lives in a bucket with public access OFF (bucket_for); otherwise it is under
    # the main public-read bucket. Either way admin viewing goes through
    # build_admin_view_url's presigned GET rather than the public URL
    # convention, so nothing links to this path except that presigned URL.
    # `kind` (selfie/id_photo) is just a filename prefix for anyone reading
    # the bucket directly — doesn't affect access control.
    ext = _EXTENSIONS[content_type]
    return f"verifications/{user_id}/{kind}-{uuid.uuid4()}.{ext}"


def media_type_from_object_path(object_path: str) -> str:
    """Derived server-side from the extension build_object_path gave the
    upload, never trusted from client input — routers/profiles.py::
    confirm_photo uses this to set Photo.media_type."""
    return "video" if object_path.lower().endswith(".mp4") else "photo"


def bucket_for(object_path: str) -> str:
    """Face-verification selfies and ID photos go to a PRIVATE bucket when one is
    configured (settings.r2_private_bucket_name): the main bucket is public-read
    (profile photos are served straight from it), and a photo of someone's ID
    card must not sit behind nothing but an unguessable URL. Unset = the single
    bucket, exactly as before."""
    if settings.r2_private_bucket_name and object_path.startswith("verifications/"):
        return settings.r2_private_bucket_name
    return settings.r2_bucket_name


def generate_upload_url(object_path: str, content_type: str) -> str:
    # ContentType is bound into the signature, so the client's PUT must send
    # the exact same Content-Type header or R2 rejects it with a signature
    # mismatch — same contract the old GCS signed URL had.
    return _get_client().generate_presigned_url(
        "put_object",
        Params={"Bucket": bucket_for(object_path), "Key": object_path, "ContentType": content_type},
        ExpiresIn=15 * 60,
    )


def build_public_url(object_path: str) -> str:
    """Bucket is public-read (R2.dev subdomain or a mapped custom domain)
    with non-guessable UUID paths — no signed GET needed, same as before."""
    return f"{settings.r2_public_url}/{object_path}"


def build_admin_view_url(object_path: str) -> str:
    """Short-lived signed GET for the face-verification admin review page —
    generated fresh per admin request rather than handing out the public
    bucket URL for something as sensitive as a person's face photo."""
    return _get_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_for(object_path), "Key": object_path},
        ExpiresIn=10 * 60,
    )


def object_exists(object_path: str) -> bool:
    """True if the object is really in the bucket - used to reject a
    submission that references a file the client never actually uploaded."""
    from botocore.exceptions import ClientError

    try:
        _get_client().head_object(Bucket=bucket_for(object_path), Key=object_path)
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def delete_object(object_path: str) -> None:
    _get_client().delete_object(Bucket=bucket_for(object_path), Key=object_path)


def delete_prefix(prefix: str) -> int:
    """Deletes every object under `prefix` (e.g. "users/<id>/"). Used when an
    account is deleted so profile photos and face-verification ID photos don't
    outlive the user. Returns how many objects were removed. Sweeps the private
    bucket too when one is configured, so files are removed wherever they live
    (including ones uploaded before the private bucket existed)."""
    client = _get_client()
    buckets = [settings.r2_bucket_name]
    if settings.r2_private_bucket_name and settings.r2_private_bucket_name not in buckets:
        buckets.append(settings.r2_private_bucket_name)
    deleted = 0
    for bucket in buckets:
        token = None
        while True:
            kwargs = {"Bucket": bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []) or []:
                client.delete_object(Bucket=bucket, Key=obj["Key"])
                deleted += 1
            if not resp.get("IsTruncated"):
                break
            token = resp.get("NextContinuationToken")
    return deleted


# ---------------------------------------------------------------- upload validation

# Exactly what build_*_object_path produces: users/<uuid>/<folder>/<uuid>.<ext>.
# A strict full-match (not startswith) so "..", "//", encoded dots, backslashes
# or another user's folder can never sneak into a stored path — object keys are
# opaque to R2, but the public URL built from one is normalised by browsers/CDNs.
_USER_OBJECT_RE = re.compile(
    r"^users/(?P<uid>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/"
    r"(?P<folder>photos|chat|stories|moments)/"
    r"(?P<name>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.(?P<ext>jpg|png|webp|mp4)$"
)

# Generous on purpose: the app lets people pick 48 MP photos and 10-second 4K clips
# straight from the camera roll without re-encoding them (a 10 s 4K60 HEVC clip is
# ~65 MB), and rejecting a legitimate upload is worse than storing a large one. The
# ceiling only has to stop absurd files, not tune quality.
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_VIDEO_BYTES = 150 * 1024 * 1024

# Top-level atoms a QuickTime/MP4 file may start with. iPhone .mov files usually open
# with "ftyp", but older or trimmed/exported ones can open with "wide", "moov", "mdat",
# "free" or "skip" - all still genuine video containers.
_VIDEO_FIRST_ATOMS = (b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip", b"pnot")


def is_valid_user_object_path(object_path: str, user_id: uuid.UUID, folder: str) -> bool:
    match = _USER_OBJECT_RE.match(object_path or "")
    return bool(match) and match["folder"] == folder and match["uid"] == str(user_id).lower()


def _is_jpeg(head: bytes) -> bool:
    return head[:3] == bytes([0xFF, 0xD8, 0xFF])


def _is_png(head: bytes) -> bool:
    return head[:8] == bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def _is_webp(head: bytes) -> bool:
    return head[:4] == b"RIFF" and head[8:12] == b"WEBP"


def _magic_ok(ext: str, head: bytes) -> bool:
    """The point is to keep non-media payloads (HTML, scripts, executables) out of
    the bucket, not to police which image format a picker produced: the app's upload
    path labels every photo image/jpeg, and a PNG screenshot or WebP that the OS
    picker hands back unconverted is still a perfectly good photo. So any image
    extension accepts any of the three image formats."""
    if ext in ("jpg", "png", "webp"):
        return _is_jpeg(head) or _is_png(head) or _is_webp(head)
    if ext == "mp4":
        return head[4:8] in _VIDEO_FIRST_ATOMS
    return False


def check_uploaded_object(object_path: str) -> str | None:
    """Confirms the client really uploaded a well-formed, reasonably sized file
    at `object_path` (which must already have passed is_valid_user_object_path).
    Presigned PUT URLs can't limit size or inspect content, so this is where an
    upload is actually vetted. Returns a short problem description, or None if
    it's fine. A rejected object is deleted so it doesn't sit in the bucket."""
    from botocore.exceptions import ClientError

    if not settings.verify_uploaded_objects:
        return None
    ext = object_path.rsplit(".", 1)[-1].lower()
    limit = MAX_VIDEO_BYTES if ext == "mp4" else MAX_IMAGE_BYTES
    client = _get_client()
    problem: str | None = None
    try:
        head = client.head_object(Bucket=bucket_for(object_path), Key=object_path)
        if head.get("ContentLength", 0) <= 0:
            problem = "empty upload"
        elif head["ContentLength"] > limit:
            problem = "file too large"
        else:
            first = client.get_object(Bucket=bucket_for(object_path), Key=object_path, Range="bytes=0-15")["Body"].read()
            if not _magic_ok(ext, first):
                problem = "file content does not match its type"
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return "file was not uploaded"
        raise
    if problem:
        try:
            client.delete_object(Bucket=bucket_for(object_path), Key=object_path)
        except Exception:  # noqa: BLE001 - best effort
            pass
    return problem
