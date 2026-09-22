import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_deleting_a_match_lets_the_same_pair_match_again(client):
    a_id, a_headers = await create_user_with_profile(client, "delmatch-a@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "delmatch-b@example.com", gender="female", interested_in="male")

    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    first = await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
    assert first.json()["matched"] is True
    match_id = first.json()["match_id"]

    delete_resp = await client.delete(f"/matches/{match_id}", headers=a_headers)
    assert delete_resp.status_code == 204

    # Gone from both sides' match list, and the swipe history was cleared —
    # a fresh like/like round trip matches them again with a NEW match id.
    assert match_id not in [m["id"] for m in (await client.get("/matches", headers=a_headers)).json()]
    assert match_id not in [m["id"] for m in (await client.get("/matches", headers=b_headers)).json()]

    again_a = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    assert again_a.json()["matched"] is False  # only one side so far, same as any fresh pair
    again_b = await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
    assert again_b.json()["matched"] is True
    assert again_b.json()["match_id"] != match_id


@pytest.mark.asyncio
async def test_deleting_a_match_after_blocking_does_not_allow_a_rematch(client):
    a_id, a_headers = await create_user_with_profile(client, "delmatch-c@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "delmatch-d@example.com", gender="female", interested_in="male")

    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    match_id = (await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})).json()["match_id"]

    assert (await client.post("/safety/block", headers=a_headers, json={"user_id": b_id})).status_code == 204
    assert (await client.delete(f"/matches/{match_id}", headers=a_headers)).status_code == 204

    # B still can't reach A at all (blocked), and — the actual point of this
    # test — trying to like A again doesn't quietly re-open the door either.
    again = await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
    assert again.status_code == 403


@pytest.mark.asyncio
async def test_deleting_a_match_after_reporting_only_keeps_discovery_exclusion(client):
    a_id, a_headers = await create_user_with_profile(client, "delmatch-e@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "delmatch-f@example.com", gender="female", interested_in="male")

    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    match_id = (await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})).json()["match_id"]

    assert (
        await client.post("/safety/report", headers=a_headers, json={"user_id": b_id, "reason": "harassment"})
    ).status_code == 204
    assert (await client.delete(f"/matches/{match_id}", headers=a_headers)).status_code == 204

    # No block here, only a report — the realistic guarantee this gives is
    # that B stays excluded from A's normal Discover deck (a swipe row from A
    # on B is still on record, same "already_swiped" exclusion discovery
    # always applies); it does not additionally lock either side out of
    # *deliberately* liking the same user_id directly, which nothing in this
    # app currently does even for a real block (blocking is the mechanism
    # for that — see test_deleting_a_match_after_blocking_does_not_allow_a_rematch).
    deck = (await client.get("/discovery/candidates", headers=a_headers)).json()
    assert b_id not in [c["user_id"] for c in deck]


@pytest.mark.asyncio
async def test_deleting_a_match_removes_its_messages_and_a_stranger_cannot_delete_it(client):
    a_id, a_headers = await create_user_with_profile(client, "delmatch-g@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "delmatch-h@example.com", gender="female", interested_in="male")
    stranger_id, stranger_headers = await create_user_with_profile(client, "delmatch-i@example.com", gender="male", interested_in="female")

    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    match_id = (await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})).json()["match_id"]

    not_found = await client.delete(f"/matches/{match_id}", headers=stranger_headers)
    assert not_found.status_code == 404

    missing = await client.delete("/matches/00000000-0000-0000-0000-000000000000", headers=a_headers)
    assert missing.status_code == 404

    assert (await client.delete(f"/matches/{match_id}", headers=b_headers)).status_code == 204
    # The match (and anything cascading from it) is gone; asking for its
    # messages 404s the same way an unknown match_id always has.
    history = await client.get(f"/matches/{match_id}/messages", headers=a_headers)
    assert history.status_code == 404
