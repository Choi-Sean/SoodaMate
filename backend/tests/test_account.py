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
