import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_delete_account_removes_user_and_profile(client):
    _, headers = await create_user_with_profile(client, "delme@example.com")

    resp = await client.delete("/account/me", headers=headers)
    assert resp.status_code == 204

    # Token is now for a deleted user — any authenticated call should fail.
    resp = await client.get("/profiles/me", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_deleted_users_email_can_be_reused_for_signup(client):
    _, headers = await create_user_with_profile(client, "reuse@example.com")
    await client.delete("/account/me", headers=headers)

    resp = await client.post("/auth/signup", json={"email": "reuse@example.com", "password": "password123"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_update_language_preference(client):
    user_id, headers = await create_user_with_profile(client, "lang1@example.com")

    resp = await client.put("/account/language", headers=headers, json={"language": "ko"})
    assert resp.status_code == 204

    from app.database import async_session_factory
    from app.models.user import User
    import uuid

    async with async_session_factory() as session:
        user = await session.get(User, uuid.UUID(user_id))
        assert user.preferred_language == "ko"


@pytest.mark.asyncio
async def test_update_language_preference_rejects_unsupported_language(client):
    _, headers = await create_user_with_profile(client, "lang2@example.com")
    resp = await client.put("/account/language", headers=headers, json={"language": "fr"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_email_for_marketing(client):
    user_id, headers = await create_user_with_profile(client, "emailupdate1@example.com")

    resp = await client.put("/account/email", headers=headers, json={"email": "marketing1@example.com"})
    assert resp.status_code == 204

    from app.database import async_session_factory
    from app.models.user import User
    import uuid

    async with async_session_factory() as session:
        user = await session.get(User, uuid.UUID(user_id))
        assert user.email == "marketing1@example.com"


@pytest.mark.asyncio
async def test_update_email_rejects_invalid_format(client):
    _, headers = await create_user_with_profile(client, "emailupdate2@example.com")
    resp = await client.put("/account/email", headers=headers, json={"email": "not-an-email"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_email_rejects_email_already_in_use(client):
    _, headers1 = await create_user_with_profile(client, "emailupdate3@example.com")
    _, headers2 = await create_user_with_profile(client, "emailupdate4@example.com")

    resp = await client.put("/account/email", headers=headers2, json={"email": "emailupdate3@example.com"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_age_restricted_report_disables_the_account_for_good(client, monkeypatch):
    """The app calls this the moment a sign-up picks a birth date under 18: the
    account is switched off, so its token stops working and the same phone
    number can't log in again to retry with another birth date."""
    import app.routers.auth as auth_router
    from tests.helpers import track_test_user

    class _Sms:
        async def start(self, phone_number):
            pass

        async def check(self, phone_number, code):
            return code == "123456"

    monkeypatch.setattr(auth_router, "sms_verifier", _Sms())
    phone = "+821098770001"
    first = await client.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
    assert first.status_code == 200
    track_test_user(first.json()["user_id"])
    headers = {"Authorization": f"Bearer {first.json()['access_token']}"}

    resp = await client.post("/account/age-restricted", headers=headers)
    assert resp.status_code == 204

    assert (await client.get("/account/me", headers=headers)).status_code in (401, 403)
    retry = await client.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
    assert retry.status_code == 403


@pytest.mark.asyncio
async def test_age_restricted_requires_login(client):
    resp = await client.post("/account/age-restricted")
    assert resp.status_code in (401, 403)
