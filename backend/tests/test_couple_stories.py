import pytest

from tests.helpers import create_user_with_profile


async def _make_match(client, email_a="csA@example.com", email_b="csB@example.com"):
    a_id, a_headers = await create_user_with_profile(client, email_a, gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, email_b, gender="female", interested_in="male")
    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    match_resp = await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
    match_id = match_resp.json()["match_id"]
    return a_id, a_headers, b_id, b_headers, match_id


@pytest.mark.asyncio
async def test_couple_story_requires_peer_confirmation_before_appearing_in_feed(client):
    a_id, a_headers, b_id, b_headers, match_id = await _make_match(client, "csA1@example.com", "csB1@example.com")

    create_resp = await client.post(
        "/couple-stories", headers=a_headers, json={"match_id": match_id, "story_text": "We met here!"}
    )
    assert create_resp.status_code == 201, create_resp.text
    story = create_resp.json()
    assert story["status"] == "pending"

    # Not visible in either side's feed yet — the peer hasn't confirmed.
    feed_before = await client.get("/couple-stories/feed", headers=b_headers)
    assert story["id"] not in [s["id"] for s in feed_before.json()]

    # A non-participant can't confirm it.
    other_id, other_headers = await create_user_with_profile(client, "csOther1@example.com")
    confirm_wrong = await client.post(f"/couple-stories/{story['id']}/confirm", headers=other_headers)
    assert confirm_wrong.status_code == 404

    confirm_resp = await client.post(f"/couple-stories/{story['id']}/confirm", headers=b_headers)
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "published"

    feed_after = await client.get("/couple-stories/feed", headers=a_headers)
    ids = [s["id"] for s in feed_after.json()]
    assert story["id"] in ids


@pytest.mark.asyncio
async def test_couple_story_declined_never_appears_in_feed(client):
    a_id, a_headers, b_id, b_headers, match_id = await _make_match(client, "csA2@example.com", "csB2@example.com")

    create_resp = await client.post(
        "/couple-stories", headers=a_headers, json={"match_id": match_id, "story_text": "story"}
    )
    story_id = create_resp.json()["id"]

    decline_resp = await client.post(f"/couple-stories/{story_id}/decline", headers=b_headers)
    assert decline_resp.status_code == 200
    assert decline_resp.json()["status"] == "declined"

    feed = await client.get("/couple-stories/feed", headers=a_headers)
    assert story_id not in [s["id"] for s in feed.json()]

    # Already resolved — can't be confirmed after being declined.
    confirm_resp = await client.post(f"/couple-stories/{story_id}/confirm", headers=b_headers)
    assert confirm_resp.status_code == 404


@pytest.mark.asyncio
async def test_only_one_story_per_match(client):
    a_id, a_headers, b_id, b_headers, match_id = await _make_match(client, "csA3@example.com", "csB3@example.com")

    first = await client.post("/couple-stories", headers=a_headers, json={"match_id": match_id, "story_text": "one"})
    assert first.status_code == 201

    second = await client.post("/couple-stories", headers=a_headers, json={"match_id": match_id, "story_text": "two"})
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_couple_story_auto_hides_past_report_threshold(client):
    a_id, a_headers, b_id, b_headers, match_id = await _make_match(client, "csA4@example.com", "csB4@example.com")

    create_resp = await client.post(
        "/couple-stories", headers=a_headers, json={"match_id": match_id, "story_text": "story"}
    )
    story_id = create_resp.json()["id"]
    await client.post(f"/couple-stories/{story_id}/confirm", headers=b_headers)

    reporters = []
    for i in range(3):
        _, headers = await create_user_with_profile(client, f"csReporter{i}@example.com")
        reporters.append(headers)

    for headers in reporters:
        resp = await client.post(f"/couple-stories/{story_id}/report", headers=headers, json={"reason": "spam"})
        assert resp.status_code == 204

    feed = await client.get("/couple-stories/feed", headers=a_headers)
    assert story_id not in [s["id"] for s in feed.json()]
