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
