import pytest

from app.routers import uploads as uploads_router
from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_presign_returns_url_and_object_path(client, monkeypatch):
    def fake_generate_upload_url(object_path: str, content_type: str) -> str:
        return f"https://storage.googleapis.com/fake-bucket/{object_path}?signature=fake"

    monkeypatch.setattr(uploads_router.storage_service, "generate_upload_url", fake_generate_upload_url)

    _, headers = await create_user_with_profile(client, "uploader@example.com")

    resp = await client.post(
        "/uploads/presign", headers=headers, json={"content_type": "image/jpeg", "position": 1}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["upload_url"].startswith("https://storage.googleapis.com/")
    assert body["gcs_object_path"].endswith(".jpg")


@pytest.mark.asyncio
async def test_presign_rejects_bad_content_type(client):
    _, headers = await create_user_with_profile(client, "uploader2@example.com")
    resp = await client.post(
        "/uploads/presign", headers=headers, json={"content_type": "application/pdf", "position": 0}
    )
    assert resp.status_code == 422
