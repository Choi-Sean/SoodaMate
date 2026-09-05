import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_block_then_report_user(client):
    a_id, a_headers = await create_user_with_profile(client, "sa@example.com")
    b_id, _ = await create_user_with_profile(client, "sb@example.com")

    resp = await client.post("/safety/block", headers=a_headers, json={"user_id": b_id})
    assert resp.status_code == 204

    resp = await client.post(
        "/safety/report",
        headers=a_headers,
        json={"user_id": b_id, "reason": "harassment", "detail": "sent unwanted messages"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_cannot_block_or_report_self(client):
    a_id, a_headers = await create_user_with_profile(client, "sc@example.com")

    resp = await client.post("/safety/block", headers=a_headers, json={"user_id": a_id})
    assert resp.status_code == 400

    resp = await client.post(
        "/safety/report", headers=a_headers, json={"user_id": a_id, "reason": "x"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_and_reregister_device_token(client):
    _, headers = await create_user_with_profile(client, "sd@example.com")

    resp = await client.post(
        "/devices/register", headers=headers, json={"fcm_token": "tok-123", "platform": "ios"}
    )
    assert resp.status_code == 204

    # Re-registering the same token (e.g. platform changed) should upsert, not conflict.
    resp = await client.post(
        "/devices/register", headers=headers, json={"fcm_token": "tok-123", "platform": "android"}
    )
    assert resp.status_code == 204
