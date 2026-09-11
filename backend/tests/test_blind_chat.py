import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_two_compatible_users_are_paired_on_second_queue_call(client):
    a_id, a_headers = await create_user_with_profile(
        client, "blindA1@example.com", gender="male", interested_in="female", age=28
    )
    b_id, b_headers = await create_user_with_profile(
        client, "blindB1@example.com", gender="female", interested_in="male", age=26
    )

    r1 = await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel", "music"]})
    assert r1.status_code == 200
    assert r1.json()["status"] == "waiting"

    r2 = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["music", "food"]})
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "matched"
    match_id = body["match_id"]
    assert match_id

    # A's queue entry is gone; A can discover the match via status polling.
    status_a = await client.get("/blind-chat/queue", headers=a_headers)
    assert status_a.json()["status"] == "matched"
    assert status_a.json()["match_id"] == match_id

    matches_a = (await client.get("/matches", headers=a_headers)).json()
    match = next(m for m in matches_a if m["id"] == match_id)
    assert match["is_blind"] is True
    assert match["blind_revealed"] is False
    assert match["blind_categories"] == ["music"]  # only the shared one
    # Name is masked to exactly "<first char>***", never the real name/photo.
    assert match["other_display_name"].endswith("***")
    assert len(match["other_display_name"]) == 4
    assert match["other_photo_url"] is None
    # No Bumble-style first-message gate for blind chat — open immediately.
    assert match["is_message_restricted"] is False
    assert match["can_send_first_message"] is True


@pytest.mark.asyncio
async def test_no_shared_category_means_no_match(client):
    _, a_headers = await create_user_with_profile(client, "blindA2@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "blindB2@example.com", gender="female", interested_in="male")

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["gaming"]})
    assert r.json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_gender_preference_mismatch_prevents_pairing(client):
    _, a_headers = await create_user_with_profile(client, "blindA3@example.com", gender="male", interested_in="female")
    # Also male, and only interested in females -> not a match for a male seeker.
    _, b_headers = await create_user_with_profile(client, "blindB3@example.com", gender="male", interested_in="female")

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel"]})
    assert r.json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_age_preference_mismatch_prevents_pairing(client):
    a_id, a_headers = await create_user_with_profile(
        client, "blindA4@example.com", gender="male", interested_in="female", age=40, min_age_pref=35, max_age_pref=45
    )
    b_id, b_headers = await create_user_with_profile(
        client, "blindB4@example.com", gender="female", interested_in="male", age=22, min_age_pref=20, max_age_pref=25
    )

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel"]})
    assert r.json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_blocked_pair_is_never_paired(client):
    import uuid

    from app.database import async_session_factory
    from app.models.interaction import Block

    a_id, a_headers = await create_user_with_profile(client, "blindA5@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "blindB5@example.com", gender="female", interested_in="male")

    async with async_session_factory() as session:
        session.add(Block(blocker_id=uuid.UUID(b_id), blocked_id=uuid.UUID(a_id)))
        await session.commit()

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel"]})
    assert r.json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_cancel_queue(client):
    _, headers = await create_user_with_profile(client, "blindCancel@example.com")
    await client.post("/blind-chat/queue", headers=headers, json={"categories": ["travel"]})
    assert (await client.get("/blind-chat/queue", headers=headers)).json()["status"] == "waiting"

    cancel = await client.delete("/blind-chat/queue", headers=headers)
    assert cancel.status_code == 204
    assert (await client.get("/blind-chat/queue", headers=headers)).json()["status"] == "idle"


@pytest.mark.asyncio
async def test_repeated_queue_call_is_idempotent(client):
    _, headers = await create_user_with_profile(client, "blindDupe@example.com")
    r1 = await client.post("/blind-chat/queue", headers=headers, json={"categories": ["travel"]})
    r2 = await client.post("/blind-chat/queue", headers=headers, json={"categories": ["music"]})
    assert r1.json()["status"] == "waiting"
    assert r2.json()["status"] == "waiting"  # no error, no duplicate entry


async def _paired_couple(client, tag_a="reveal", tag_b="reveal", age_a=28, age_b=26):
    a_id, a_headers = await create_user_with_profile(
        client, f"{tag_a}A@example.com", display_name=f"{tag_a}A", gender="male", interested_in="female", age=age_a
    )
    b_id, b_headers = await create_user_with_profile(
        client, f"{tag_b}B@example.com", display_name=f"{tag_b}B", gender="female", interested_in="male", age=age_b
    )
    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel"]})
    match_id = r.json()["match_id"]
    return a_id, a_headers, b_id, b_headers, match_id


@pytest.mark.asyncio
async def test_only_eligible_side_can_request_reveal_in_mixed_pair(client):
    a_id, a_headers, b_id, b_headers, match_id = await _paired_couple(client, "revealA", "revealB")

    # A is male -> not eligible in a mixed pair (only the female side is).
    forbidden = await client.post(f"/matches/{match_id}/blind-reveal/request", headers=a_headers)
    assert forbidden.status_code == 403

    ok = await client.post(f"/matches/{match_id}/blind-reveal/request", headers=b_headers)
    assert ok.status_code == 200
    assert ok.json()["reveal_requested_by_me"] is True
    assert ok.json()["blind_revealed"] is False

    # A should now see an incoming request.
    a_view = (await client.get("/matches", headers=a_headers)).json()
    match_a = next(m for m in a_view if m["id"] == match_id)
    assert match_a["has_incoming_reveal_request"] is True


@pytest.mark.asyncio
async def test_reveal_accept_unmasks_both_sides_but_not_self_accept(client):
    a_id, a_headers, b_id, b_headers, match_id = await _paired_couple(client, "revealC", "revealD")

    await client.post(f"/matches/{match_id}/blind-reveal/request", headers=b_headers)

    # The requester can't accept their own request.
    self_accept = await client.post(f"/matches/{match_id}/blind-reveal/accept", headers=b_headers)
    assert self_accept.status_code == 400

    accept = await client.post(f"/matches/{match_id}/blind-reveal/accept", headers=a_headers)
    assert accept.status_code == 200
    assert accept.json()["blind_revealed"] is True
    assert accept.json()["other_display_name"] == "revealDB"  # real name, no longer masked
    assert accept.json()["other_photo_url"] is not None

    b_view = (await client.get("/matches", headers=b_headers)).json()
    match_b = next(m for m in b_view if m["id"] == match_id)
    assert match_b["blind_revealed"] is True
    assert match_b["other_display_name"] == "revealCA"


def test_blind_chat_messaging_open_immediately_no_first_message_gate():
    """Real WS round-trip (mirrors test_chat_ws.py's pattern, hence the
    plain TestClient / non-async style) — the male side of a mixed pair is
    normally blocked from sending first (Phase 14's Bumble rule), but a
    blind-chat match has no such gate: either side can start immediately."""
    from datetime import date

    from starlette.testclient import TestClient

    from app.main import app
    from tests.helpers import track_test_user

    def _signup_and_complete(client, email, gender, interested_in):
        signup = client.post("/auth/signup", json={"email": email, "password": "password123"})
        tokens = signup.json()
        track_test_user(tokens["user_id"])
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        birth_year = date.today().year - 27
        client.put(
            "/profiles/me",
            headers=headers,
            json={
                "display_name": "Test",
                "legal_first_name": "Test",
                "birth_date": f"{birth_year}-01-01",
                "gender": gender,
                "interested_in": interested_in,
                "min_age_pref": 18,
                "max_age_pref": 99,
            },
        )
        client.post(
            "/profiles/me/photos/confirm",
            headers=headers,
            json={"gcs_object_path": f"users/{tokens['user_id']}/photos/0.jpg", "position": 0},
        )
        return tokens["user_id"], tokens["access_token"]

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete(tc, "blindWsA@example.com", "male", "female")
        b_id, b_token = _signup_and_complete(tc, "blindWsB@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
        r = tc.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel"]})
        match_id = r.json()["match_id"]
        assert match_id

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # Male sends first — would be rejected on a normal swipe
                # match, must succeed here.
                ws_a.send_json({"type": "message", "match_id": match_id, "content": "hi, shall we talk?"})
                received = ws_b.receive_json()
                assert received["type"] == "message"
                assert received["content"] == "hi, shall we talk?"
