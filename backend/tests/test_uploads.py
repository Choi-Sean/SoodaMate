import pytest

from app.routers import uploads as uploads_router
from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_presign_returns_url_and_object_path(client, monkeypatch):
    def fake_generate_upload_url(object_path: str, content_type: str) -> str:
        return f"https://fake-account.r2.cloudflarestorage.com/fake-bucket/{object_path}?signature=fake"

    monkeypatch.setattr(uploads_router.storage_service, "generate_upload_url", fake_generate_upload_url)

    _, headers = await create_user_with_profile(client, "uploader@example.com")

    resp = await client.post(
        "/uploads/presign", headers=headers, json={"content_type": "image/jpeg", "position": 1}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["upload_url"].startswith("https://fake-account.r2.cloudflarestorage.com/")
    assert body["gcs_object_path"].endswith(".jpg")


@pytest.mark.asyncio
async def test_presign_rejects_bad_content_type(client):
    _, headers = await create_user_with_profile(client, "uploader2@example.com")
    resp = await client.post(
        "/uploads/presign", headers=headers, json={"content_type": "application/pdf", "position": 0}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_presign_accepts_video_mp4(client, monkeypatch):
    monkeypatch.setattr(
        uploads_router.storage_service,
        "generate_upload_url",
        lambda object_path, content_type: f"https://fake.r2.cloudflarestorage.com/{object_path}",
    )
    _, headers = await create_user_with_profile(client, "uploader3@example.com")
    resp = await client.post(
        "/uploads/presign", headers=headers, json={"content_type": "video/mp4", "position": 1}
    )
    assert resp.status_code == 200
    assert resp.json()["gcs_object_path"].endswith(".mp4")


@pytest.mark.asyncio
async def test_confirm_photo_derives_media_type_from_extension(client):
    _, headers = await create_user_with_profile(client, "uploader4@example.com")

    photo_confirm = await client.post(
        "/profiles/me/photos/confirm",
        headers=headers,
        json={"gcs_object_path": "users/x/photos/a.jpg", "position": 1},
    )
    assert photo_confirm.status_code == 201
    assert photo_confirm.json()["media_type"] == "photo"

    video_confirm = await client.post(
        "/profiles/me/photos/confirm",
        headers=headers,
        json={"gcs_object_path": "users/x/photos/b.mp4", "position": 2},
    )
    assert video_confirm.status_code == 201
    assert video_confirm.json()["media_type"] == "video"

    me = await client.get("/profiles/me", headers=headers)
    media_types = {p["gcs_object_path"]: p["media_type"] for p in me.json()["photos"]}
    assert media_types["users/x/photos/a.jpg"] == "photo"
    assert media_types["users/x/photos/b.mp4"] == "video"
