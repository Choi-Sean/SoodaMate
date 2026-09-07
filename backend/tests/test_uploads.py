import uuid

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


@pytest.mark.asyncio
async def test_display_name_locked_after_initial_creation(client):
    _, headers = await create_user_with_profile(
        client, "namelock@example.com", display_name="Original", gender="male"
    )
    original = (await client.get("/profiles/me", headers=headers)).json()

    resp = await client.put(
        "/profiles/me",
        headers=headers,
        json={
            "display_name": "Changed",
            "legal_first_name": "Changed",
            "birth_date": "2000-01-01",
            "gender": "female",
            "interested_in": "female",
        },
    )
    assert resp.status_code == 200
    # Every attempted change here is silently ignored, not merged — the
    # backend is the enforcement point regardless of what the client sends.
    # A real change goes through support@soodamate.com (photo ID required),
    # not this endpoint.
    assert resp.json()["display_name"] == "Original"
    assert resp.json()["legal_first_name"] == "Original"
    assert resp.json()["birth_date"] == original["birth_date"]
    assert resp.json()["gender"] == "male"


@pytest.mark.asyncio
async def test_reorder_photos(client):
    _, headers = await create_user_with_profile(client, "reorder@example.com")

    ids = []
    for pos in range(3):
        resp = await client.post(
            "/profiles/me/photos/confirm",
            headers=headers,
            json={"gcs_object_path": f"users/x/photos/{pos}.jpg", "position": pos},
        )
        ids.append(resp.json()["id"])

    # ids[0] is already position 0 from create_user_with_profile's own photo
    # at position 0 -- fetch the real current ordering first.
    me = await client.get("/profiles/me", headers=headers)
    current = sorted(me.json()["photos"], key=lambda p: p["position"])
    current_ids = [p["id"] for p in current]

    reversed_ids = list(reversed(current_ids))
    resp = await client.put("/profiles/me/photos/reorder", headers=headers, json={"photo_ids": reversed_ids})
    assert resp.status_code == 200
    body = resp.json()
    assert [p["id"] for p in sorted(body, key=lambda p: p["position"])] == reversed_ids


@pytest.mark.asyncio
async def test_last_photo_cannot_be_deleted(client):
    _, headers = await create_user_with_profile(client, "lastphoto@example.com")

    # create_user_with_profile's helper already confirms one photo at
    # position 0 — that's the only one this user has.
    me = await client.get("/profiles/me", headers=headers)
    only_photo_id = me.json()["photos"][0]["id"]

    resp = await client.delete(f"/profiles/me/photos/{only_photo_id}", headers=headers)
    assert resp.status_code == 400

    me_after = await client.get("/profiles/me", headers=headers)
    assert len(me_after.json()["photos"]) == 1


@pytest.mark.asyncio
async def test_reorder_photos_rejects_incomplete_list(client):
    _, headers = await create_user_with_profile(client, "reorder2@example.com")
    resp = await client.put(
        "/profiles/me/photos/reorder", headers=headers, json={"photo_ids": [str(uuid.uuid4())]}
    )
    assert resp.status_code == 400
