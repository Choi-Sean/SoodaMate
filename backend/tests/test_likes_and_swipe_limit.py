import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_swipe_limit_decrements_and_blocks_at_20(client):
    _, a_headers = await create_user_with_profile(client, "limit-a@example.com", gender="male", interested_in="female")

    status0 = (await client.get("/interactions/swipe-limit", headers=a_headers)).json()
    assert status0 == {"remaining": 20, "limit": 20, "resets_at": None}

    # sp_RecordSwipe only needs a valid FK on the target, not a complete
    # profile — bare signups are enough here and cut the request count way
    # down (this test already does 21 real signups against the live DB).
    for i in range(20):
        signup = await client.post("/auth/signup", json={"email": f"limit-target{i}@example.com", "password": "password123"})
        target_id = signup.json()["user_id"]
        resp = await client.post("/interactions/pass", headers=a_headers, json={"to_user_id": target_id})
        assert resp.status_code == 200

    status20 = (await client.get("/interactions/swipe-limit", headers=a_headers)).json()
    assert status20["remaining"] == 0
    assert status20["resets_at"] is not None

    signup21 = await client.post("/auth/signup", json={"email": "limit-target20@example.com", "password": "password123"})
    one_more = signup21.json()["user_id"]
    resp21 = await client.post("/interactions/pass", headers=a_headers, json={"to_user_id": one_more})
    assert resp21.status_code == 429
    assert resp21.json()["detail"]["resets_at"] is not None


@pytest.mark.asyncio
async def test_liked_me_excludes_already_matched_and_already_responded(client):
    a_id, a_headers = await create_user_with_profile(client, "liked-a@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "liked-b@example.com", gender="female", interested_in="male")
    c_id, c_headers = await create_user_with_profile(client, "liked-c@example.com", gender="female", interested_in="male")

    await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
    await client.post("/interactions/superlike", headers=c_headers, json={"to_user_id": a_id})

    liked_me = (await client.get("/discovery/liked-me", headers=a_headers)).json()
    liked_me_ids = {c["user_id"] for c in liked_me}
    assert liked_me_ids == {b_id, c_id}
    c_entry = next(c for c in liked_me if c["user_id"] == c_id)
    assert c_entry["superliked_me"] is True

    # A likes B back -> instant match (B already liked A) -> B drops out of
    # A's liked-me (already matched), C should remain.
    match_resp = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    assert match_resp.json()["matched"] is True

    liked_me_after_match = (await client.get("/discovery/liked-me", headers=a_headers)).json()
    assert {c["user_id"] for c in liked_me_after_match} == {c_id}

    # A passes on C -> C also drops out (already responded, even though rejected).
    await client.post("/interactions/pass", headers=a_headers, json={"to_user_id": c_id})
    liked_me_after_pass = (await client.get("/discovery/liked-me", headers=a_headers)).json()
    assert liked_me_after_pass == []


@pytest.mark.asyncio
async def test_matches_include_other_users_photo_url(client):
    a_id, a_headers = await create_user_with_profile(client, "photo-a@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "photo-b@example.com", gender="female", interested_in="male")

    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})

    matches = (await client.get("/matches", headers=a_headers)).json()
    assert len(matches) == 1
    assert matches[0]["other_photo_url"] is not None
    # Full host depends on R2_PUBLIC_URL, which isn't set in the test env —
    # just confirm the object path landed in the URL.
    assert "photos/0.jpg" in matches[0]["other_photo_url"]
