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
    # No SMTP_HOST configured in test env -> the real sender raises, not a
    # silent no-op (unlike push_service's pattern) since a code that never
    # arrives is worse than an honest error.
    assert resp.status_code == 500


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
