import pytest

from tests.helpers import create_user_with_profile


class FakeSender:
    def __init__(self):
        self.sent = []

    async def send(self, to, subject, body):
        self.sent.append((to, subject, body))


@pytest.mark.asyncio
async def test_rejects_personal_email_domain(client):
    _, headers = await create_user_with_profile(client, "ver1@example.com")
    resp = await client.post(
        "/verification/start", headers=headers, json={"kind": "work", "email": "someone@gmail.com"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_start_fails_loudly_when_smtp_unconfigured(client):
    _, headers = await create_user_with_profile(client, "ver2@example.com")
    resp = await client.post(
        "/verification/start", headers=headers, json={"kind": "work", "email": "me@acmecorp.com"}
    )
    # No SMTP_HOST configured in test env -> the real sender raises an
    # HTTPException(503), not a silent no-op (unlike push_service's pattern),
    # since a code that never arrives is worse than an honest error. Same
    # "not configured yet" status as payments' test_checkout_session_requires_configured_stripe.
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_full_verification_flow_with_mocked_sender(client, monkeypatch):
    import app.routers.verification as verification_router

    fake_sender = FakeSender()
    monkeypatch.setattr(verification_router, "email_sender", fake_sender)

    _, headers = await create_user_with_profile(client, "ver3@example.com")
    resp = await client.post(
        "/verification/start", headers=headers, json={"kind": "school", "email": "me@university.edu"}
    )
    assert resp.status_code == 204
    assert len(fake_sender.sent) == 1
    sent_body = fake_sender.sent[0][2]
    code = "".join(ch for ch in sent_body if ch.isdigit())[:6]

    wrong = await client.post("/verification/confirm", headers=headers, json={"kind": "school", "code": "000000"})
    assert wrong.status_code in (400, 429)

    confirm = await client.post("/verification/confirm", headers=headers, json={"kind": "school", "code": code})
    assert confirm.status_code == 204

    profile = await client.get("/profiles/me", headers=headers)
    assert profile.json()["verified_badge"] == "school"


@pytest.mark.asyncio
async def test_face_verification_submit_and_admin_approve_flow(client, monkeypatch):
    import app.routers.verification as verification_router

    monkeypatch.setattr(
        verification_router.storage_service,
        "generate_upload_url",
        lambda object_path, content_type: f"https://fake.r2.cloudflarestorage.com/{object_path}",
    )

    user_id, headers = await create_user_with_profile(client, "faceverify1@example.com")

    presign = await client.post("/verification/face/presign", headers=headers, json={"content_type": "image/jpeg"})
    assert presign.status_code == 200
    object_path = presign.json()["gcs_object_path"]
    assert object_path.startswith(f"verifications/{user_id}/")

    submit = await client.post("/verification/face/submit", headers=headers, json={"gcs_object_path": object_path})
    assert submit.status_code == 201
    assert submit.json()["status"] == "pending"

    status_resp = await client.get("/verification/face/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "pending"

    # Not an admin yet -> the review endpoints must refuse.
    listing = await client.get("/admin/face-verifications", headers=headers)
    assert listing.status_code == 403

    from app.database import async_session_factory
    from app.models.user import User
    import uuid as uuid_mod

    async with async_session_factory() as session:
        user = await session.get(User, uuid_mod.UUID(user_id))
        user.is_admin = True
        await session.commit()

    import app.schemas.verification as verification_schemas

    monkeypatch.setattr(
        verification_schemas, "build_admin_view_url", lambda object_path: f"https://signed.example/{object_path}"
    )

    pending = await client.get("/admin/face-verifications?status=pending", headers=headers)
    assert pending.status_code == 200
    items = pending.json()
    assert len(items) == 1
    assert items[0]["user_id"] == user_id
    assert items[0]["view_url"].startswith("https://signed.example/")

    verification_id = items[0]["id"]
    approve = await client.post(f"/admin/face-verifications/{verification_id}/approve", headers=headers)
    assert approve.status_code == 204

    profile = await client.get("/profiles/me", headers=headers)
    assert profile.json()["face_verified"] is True

    approved_list = await client.get("/admin/face-verifications?status=approved", headers=headers)
    assert len(approved_list.json()) == 1
    still_pending = await client.get("/admin/face-verifications?status=pending", headers=headers)
    assert len(still_pending.json()) == 0


@pytest.mark.asyncio
async def test_face_verification_reject_clears_badge(client, monkeypatch):
    import app.routers.verification as verification_router

    monkeypatch.setattr(
        verification_router.storage_service,
        "generate_upload_url",
        lambda object_path, content_type: f"https://fake.r2.cloudflarestorage.com/{object_path}",
    )
    import app.schemas.verification as verification_schemas

    monkeypatch.setattr(
        verification_schemas, "build_admin_view_url", lambda object_path: f"https://signed.example/{object_path}"
    )

    user_id, headers = await create_user_with_profile(client, "faceverify2@example.com")
    presign = await client.post("/verification/face/presign", headers=headers, json={"content_type": "image/jpeg"})
    object_path = presign.json()["gcs_object_path"]
    await client.post("/verification/face/submit", headers=headers, json={"gcs_object_path": object_path})

    from app.database import async_session_factory
    from app.models.user import User
    import uuid as uuid_mod

    async with async_session_factory() as session:
        user = await session.get(User, uuid_mod.UUID(user_id))
        user.is_admin = True
        await session.commit()

    pending = await client.get("/admin/face-verifications?status=pending", headers=headers)
    verification_id = pending.json()[0]["id"]

    reject = await client.post(f"/admin/face-verifications/{verification_id}/reject", headers=headers)
    assert reject.status_code == 204

    profile = await client.get("/profiles/me", headers=headers)
    assert profile.json()["face_verified"] is False


@pytest.mark.asyncio
async def test_lockout_after_too_many_wrong_attempts(client, monkeypatch):
    import app.routers.verification as verification_router

    fake_sender = FakeSender()
    monkeypatch.setattr(verification_router, "email_sender", fake_sender)

    _, headers = await create_user_with_profile(client, "ver4@example.com")
    await client.post("/verification/start", headers=headers, json={"kind": "work", "email": "me@acmecorp.com"})

    last_status = None
    for _ in range(6):
        resp = await client.post("/verification/confirm", headers=headers, json={"kind": "work", "code": "111111"})
        last_status = resp.status_code
    assert last_status == 429
