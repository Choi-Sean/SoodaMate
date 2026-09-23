import pytest

from tests.helpers import create_ordinary_match, create_user_with_profile


@pytest.mark.asyncio
async def test_like_is_discontinued(client):
    """Classic Matching's swipe/discovery UI has no reachable entry point
    anywhere in the app anymore — /interactions/like is discontinued rather
    than left live-but-unreachable (see routers/interactions.py)."""
    _, a_headers = await create_user_with_profile(client, "discA1@example.com", gender="male", interested_in="female")
    b_id, _ = await create_user_with_profile(client, "discB1@example.com", gender="female", interested_in="male")

    resp = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_superlike_is_discontinued(client):
    _, a_headers = await create_user_with_profile(client, "discA2@example.com", gender="male", interested_in="female")
    b_id, _ = await create_user_with_profile(client, "discB2@example.com", gender="female", interested_in="male")

    resp = await client.post("/interactions/superlike", headers=a_headers, json={"to_user_id": b_id})
    assert resp.status_code == 410


@pytest.mark.asyncio
async def test_pass_still_works_and_never_matches(client):
    a_id, a_headers = await create_user_with_profile(client, "a3@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "b3@example.com", gender="female", interested_in="male")

    resp_a = await client.post("/interactions/pass", headers=a_headers, json={"to_user_id": b_id})
    assert resp_a.status_code == 200
    assert resp_a.json()["matched"] is False

    resp_b = await client.post("/interactions/pass", headers=b_headers, json={"to_user_id": a_id})
    assert resp_b.json()["matched"] is False

    a_matches = (await client.get("/matches", headers=a_headers)).json()
    assert a_matches == []


@pytest.mark.asyncio
async def test_cannot_pass_on_self(client):
    a_id, a_headers = await create_user_with_profile(client, "a4@example.com")
    resp = await client.post("/interactions/pass", headers=a_headers, json={"to_user_id": a_id})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_blocked_user_cannot_be_passed_on(client):
    import uuid

    from app.database import async_session_factory
    from app.models.interaction import Block

    a_id, a_headers = await create_user_with_profile(client, "a5@example.com", gender="male", interested_in="female")
    b_id, _ = await create_user_with_profile(client, "b5@example.com", gender="female", interested_in="male")

    async with async_session_factory() as session:
        session.add(Block(blocker_id=uuid.UUID(b_id), blocked_id=uuid.UUID(a_id)))
        await session.commit()

    resp = await client.post("/interactions/pass", headers=a_headers, json={"to_user_id": b_id})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_pass_on_nonexistent_user_is_404_not_500(client):
    """A candidate deleted after the deck was fetched -> a clean 404, not an
    unhandled FK IntegrityError 500 from sp_RecordSwipe."""
    _, headers = await create_user_with_profile(client, "swipe-ghost@example.com")
    resp = await client.post(
        "/interactions/pass",
        headers=headers,
        json={"to_user_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mutual_like_still_creates_a_real_match_when_invoked_directly(client):
    """record_swipe's own match-creation logic (still real, live code —
    tests/helpers.create_ordinary_match calls it directly, bypassing the now-
    discontinued HTTP endpoints above) still works: a real Match row visible
    to both sides, same as if a user had actually swiped."""
    a_id, a_headers = await create_user_with_profile(client, "a2@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "b2@example.com", gender="female", interested_in="male")

    match_id = await create_ordinary_match(a_id, b_id)
    assert match_id

    a_matches = (await client.get("/matches", headers=a_headers)).json()
    b_matches = (await client.get("/matches", headers=b_headers)).json()
    assert any(m["id"] == match_id and m["other_user_id"] == b_id for m in a_matches)
    assert any(m["id"] == match_id and m["other_user_id"] == a_id for m in b_matches)
