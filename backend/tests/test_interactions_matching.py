import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_one_sided_like_does_not_match(client):
    _, a_headers = await create_user_with_profile(client, "a1@example.com", gender="male", interested_in="female")
    b_id, _ = await create_user_with_profile(client, "b1@example.com", gender="female", interested_in="male")

    resp = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    assert resp.status_code == 200
    assert resp.json()["matched"] is False


@pytest.mark.asyncio
async def test_mutual_like_creates_match_visible_to_both(client):
    a_id, a_headers = await create_user_with_profile(client, "a2@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "b2@example.com", gender="female", interested_in="male")

    resp1 = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    assert resp1.json()["matched"] is False

    resp2 = await client.post("/interactions/superlike", headers=b_headers, json={"to_user_id": a_id})
    assert resp2.json()["matched"] is True
    match_id = resp2.json()["match_id"]
    assert match_id is not None

    a_matches = (await client.get("/matches", headers=a_headers)).json()
    b_matches = (await client.get("/matches", headers=b_headers)).json()
    assert any(m["id"] == match_id and m["other_user_id"] == b_id for m in a_matches)
    assert any(m["id"] == match_id and m["other_user_id"] == a_id for m in b_matches)


@pytest.mark.asyncio
async def test_like_then_pass_does_not_match(client):
    a_id, a_headers = await create_user_with_profile(client, "a3@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "b3@example.com", gender="female", interested_in="male")

    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    resp = await client.post("/interactions/pass", headers=b_headers, json={"to_user_id": a_id})
    assert resp.json()["matched"] is False

    a_matches = (await client.get("/matches", headers=a_headers)).json()
    assert a_matches == []


@pytest.mark.asyncio
async def test_cannot_swipe_on_self(client):
    a_id, a_headers = await create_user_with_profile(client, "a4@example.com")
    resp = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": a_id})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_blocked_user_cannot_be_swiped(client):
    import uuid

    from app.database import async_session_factory
    from app.models.interaction import Block

    a_id, a_headers = await create_user_with_profile(client, "a5@example.com", gender="male", interested_in="female")
    b_id, _ = await create_user_with_profile(client, "b5@example.com", gender="female", interested_in="male")

    async with async_session_factory() as session:
        session.add(Block(blocker_id=uuid.UUID(b_id), blocked_id=uuid.UUID(a_id)))
        await session.commit()

    resp = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    assert resp.status_code == 403
