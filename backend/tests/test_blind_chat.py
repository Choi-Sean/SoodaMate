import uuid
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
async def test_no_shared_category_still_matches(client):
    """Category is a topic preference, not a hard filter — with a small
    early user base, requiring overlap left most queues matching nobody at
    all. Two otherwise-compatible users with zero shared categories should
    still pair, just with an empty blind_categories (nothing in common to
    show as a shared-topic icebreaker)."""
    _, a_headers = await create_user_with_profile(client, "blindA2@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "blindB2@example.com", gender="female", interested_in="male")

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["gaming"]})
    assert r.json()["status"] == "matched"

    matches_a = (await client.get("/matches", headers=a_headers)).json()
    match = next(m for m in matches_a if m["id"] == r.json()["match_id"])
    assert match["blind_categories"] == []


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
    assert accept.json()["other_age"] == 26  # B was created with age_b=26
    assert accept.json()["other_gender"] == "female"

    b_view = (await client.get("/matches", headers=b_headers)).json()
    match_b = next(m for m in b_view if m["id"] == match_id)
    assert match_b["blind_revealed"] is True
    assert match_b["other_display_name"] == "revealCA"
    assert match_b["other_age"] == 28  # A was created with age_a=28
    assert match_b["other_gender"] == "male"


@pytest.mark.asyncio
async def test_pre_reveal_shows_age_gender_mbti_and_bio1_but_masks_name_photo_bio2_bio3(client):
    a_id, a_headers, b_id, b_headers, match_id = await _paired_couple(client, "maskA", "maskB", age_a=31, age_b=24)
    await client.put(
        "/profiles/me",
        headers=b_headers,
        json={
            "display_name": "maskBB", "legal_first_name": "maskBB", "birth_date": "2001-01-01",
            "gender": "female", "interested_in": "male", "min_age_pref": 18, "max_age_pref": 99,
            "bio": "bio one", "bio2": "bio two", "bio3": "bio three", "mbti": "ENFP",
        },
    )

    view = (await client.get("/matches", headers=a_headers)).json()
    match = next(m for m in view if m["id"] == match_id)
    assert match["other_display_name"] == "M***"  # masked, not the real "maskBB"
    assert match["other_photo_url"] is None
    assert match["other_age"] == 24
    assert match["other_gender"] == "female"
    assert match["other_mbti"] == "ENFP"
    assert match["other_bio"] == "bio one"
    assert match["other_bio2"] is None
    assert match["other_bio3"] is None

    await client.post(f"/matches/{match_id}/blind-reveal/request", headers=b_headers)
    revealed = (await client.post(f"/matches/{match_id}/blind-reveal/accept", headers=a_headers)).json()
    assert revealed["other_display_name"] == "maskBB"
    assert revealed["other_photo_url"] is not None
    assert revealed["other_bio2"] == "bio two"
    assert revealed["other_bio3"] == "bio three"


@pytest.mark.asyncio
async def test_match_profile_endpoint_blocked_until_revealed_then_returns_full_profile(client):
    a_id, a_headers, b_id, b_headers, match_id = await _paired_couple(client, "profE", "profF", age_a=30, age_b=27)

    still_blind = await client.get(f"/matches/{match_id}/profile", headers=a_headers)
    assert still_blind.status_code == 403

    await client.post(f"/matches/{match_id}/blind-reveal/request", headers=b_headers)
    await client.post(f"/matches/{match_id}/blind-reveal/accept", headers=a_headers)

    a_view = await client.get(f"/matches/{match_id}/profile", headers=a_headers)
    assert a_view.status_code == 200
    body = a_view.json()
    assert body["display_name"] == "profFB"
    assert body["age"] == 27
    assert body["gender"] == "female"
    assert len(body["photos"]) == 1

    not_found = await client.get(f"/matches/{uuid.uuid4()}/profile", headers=a_headers)
    assert not_found.status_code == 404


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
            json={"gcs_object_path": f"users/{tokens['user_id']}/photos/{uuid.uuid4()}.jpg", "position": 0},
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


@pytest.mark.asyncio
async def test_distance_filter_excludes_far_then_allows_close(client):
    # Seoul-ish coordinates for A; B starts ~1500km away (Tokyo-ish), then a
    # second B-equivalent candidate is placed a few km from A.
    a_id, a_headers = await create_user_with_profile(
        client, "distA@example.com", gender="male", interested_in="female", location_lat=37.5665, location_lng=126.9780
    )
    _, far_b_headers = await create_user_with_profile(
        client, "distFarB@example.com", gender="female", interested_in="male", location_lat=35.6762, location_lng=139.6503
    )

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"], "max_distance_km": 50})
    r = await client.post("/blind-chat/queue", headers=far_b_headers, json={"categories": ["travel"]})
    assert r.json()["status"] == "waiting"  # too far — no match despite category overlap

    _, near_b_headers = await create_user_with_profile(
        client, "distNearB@example.com", gender="female", interested_in="male", location_lat=37.55, location_lng=126.99
    )
    r2 = await client.post("/blind-chat/queue", headers=near_b_headers, json={"categories": ["travel"]})
    assert r2.json()["status"] == "matched"


@pytest.mark.asyncio
async def test_session_gender_filter_narrows_all_preference(client):
    # A's profile-level preference is "all", but this session explicitly
    # asks for female only — a waiting male shouldn't be picked.
    a_id, a_headers = await create_user_with_profile(client, "genderA@example.com", gender="male", interested_in="all")
    _, male_headers = await create_user_with_profile(client, "genderMaleB@example.com", gender="male", interested_in="all")

    await client.post(
        "/blind-chat/queue", headers=a_headers, json={"categories": ["travel"], "gender": "female"}
    )
    r = await client.post("/blind-chat/queue", headers=male_headers, json={"categories": ["travel"]})
    assert r.json()["status"] == "waiting"  # A only wants female this session — no match

    _, female_headers = await create_user_with_profile(client, "genderFemaleB@example.com", gender="female", interested_in="all")
    r2 = await client.post("/blind-chat/queue", headers=female_headers, json={"categories": ["travel"]})
    assert r2.json()["status"] == "matched"


@pytest.mark.asyncio
async def test_session_age_filter_narrows_profile_default(client):
    a_id, a_headers = await create_user_with_profile(
        client, "ageA@example.com", gender="male", interested_in="female", age=30, min_age_pref=18, max_age_pref=99
    )
    _, older_headers = await create_user_with_profile(
        client, "ageOlderB@example.com", gender="female", interested_in="male", age=40
    )
    await client.post(
        "/blind-chat/queue", headers=a_headers, json={"categories": ["travel"], "min_age": 25, "max_age": 32}
    )
    r = await client.post("/blind-chat/queue", headers=older_headers, json={"categories": ["travel"]})
    assert r.json()["status"] == "waiting"  # 40 is outside this session's 25-32 window

    _, younger_headers = await create_user_with_profile(
        client, "ageYoungerB@example.com", gender="female", interested_in="male", age=28
    )
    r2 = await client.post("/blind-chat/queue", headers=younger_headers, json={"categories": ["travel"]})
    assert r2.json()["status"] == "matched"


async def _match_and_leave(client, a_headers, b_headers, categories):
    """Pairs A and B on the given categories, then also resolves A's own
    queue entry (GET, same as the waiting side's poll) so it doesn't linger
    matched-but-unconsumed and short-circuit A's *next* join_queue call —
    join_queue treats any existing row (even an already-matched one) as
    "nothing to do, just resolve it," so a caller that joins A repeatedly
    must drain each match the same way the real client would."""
    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": categories})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": categories})
    assert r.json()["status"] == "matched"
    await client.get("/blind-chat/queue", headers=a_headers)


@pytest.mark.asyncio
async def test_free_daily_blind_match_limit_then_unlimited_bypasses_it(client):
    _, a_headers = await create_user_with_profile(client, "limitA@example.com", gender="male", interested_in="female")

    limit0 = await client.get("/blind-chat/limit", headers=a_headers)
    assert limit0.json() == {
        "remaining": 5,
        "limit": 5,
        "resets_at": None,
        "unlimited": False,
        "bonus_available": True,
    }

    for i in range(5):
        _, b_headers = await create_user_with_profile(
            client, f"limitB{i}@example.com", gender="female", interested_in="male"
        )
        await _match_and_leave(client, a_headers, b_headers, ["travel"])

    limit3 = await client.get("/blind-chat/limit", headers=a_headers)
    assert limit3.json()["remaining"] == 0

    _, b4_headers = await create_user_with_profile(client, "limitB5@example.com", gender="female", interested_in="male")
    blocked = await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    assert blocked.status_code == 429

    # Grant unlimited matching directly (mirrors how the webhook would set
    # it) and confirm the same user can now match past the free cap.
    import uuid as uuid_mod
    from datetime import datetime, timedelta, timezone

    from app.database import async_session_factory
    from app.models.profile import Profile

    a_id = (await client.get("/profiles/me", headers=a_headers)).json()["user_id"]
    async with async_session_factory() as session:
        profile = await session.get(Profile, uuid_mod.UUID(a_id))
        profile.unlimited_matching_until = datetime.now(timezone.utc) + timedelta(days=1)
        await session.commit()

    limit_unlimited = await client.get("/blind-chat/limit", headers=a_headers)
    assert limit_unlimited.json()["unlimited"] is True

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    unblocked = await client.post("/blind-chat/queue", headers=b4_headers, json={"categories": ["travel"]})
    assert unblocked.json()["status"] == "matched"


@pytest.mark.asyncio
async def test_blind_chat_ad_bonus_grants_one_extra_match_once_per_day(client):
    _, headers = await create_user_with_profile(client, "adbonus@example.com")

    limit0 = await client.get("/blind-chat/limit", headers=headers)
    assert limit0.json() == {
        "remaining": 5,
        "limit": 5,
        "resets_at": None,
        "unlimited": False,
        "bonus_available": True,
    }

    claimed = await client.post("/blind-chat/ad-bonus", headers=headers)
    assert claimed.json() == {
        "remaining": 6,
        "limit": 6,
        "resets_at": None,
        "unlimited": False,
        "bonus_available": False,
    }

    # Watching a second ad the same day doesn't stack a second bonus.
    claimed_again = await client.post("/blind-chat/ad-bonus", headers=headers)
    assert claimed_again.json()["limit"] == 6
    assert claimed_again.json()["bonus_available"] is False

    limit_after = await client.get("/blind-chat/limit", headers=headers)
    assert limit_after.json()["limit"] == 6
    assert limit_after.json()["bonus_available"] is False


@pytest.mark.asyncio
async def test_ai_match_requires_credit(client):
    _, headers = await create_user_with_profile(client, "aimatchNoCred@example.com")
    resp = await client.post("/blind-chat/ai-match", headers=headers, json={"categories": ["travel"]})
    assert resp.status_code == 402


@pytest.mark.asyncio
async def test_ai_match_no_candidates_leaves_credit_untouched(client):
    import uuid as uuid_mod

    from app.database import async_session_factory
    from app.models.profile import Profile

    user_id, headers = await create_user_with_profile(client, "aimatchEmpty@example.com")
    async with async_session_factory() as session:
        profile = await session.get(Profile, uuid_mod.UUID(user_id))
        profile.ai_match_credits = 1
        await session.commit()

    resp = await client.post("/blind-chat/ai-match", headers=headers, json={"categories": ["travel"]})
    assert resp.status_code == 200
    assert resp.json() == {"found": False, "match": None}

    balance = await client.get("/payments/balance", headers=headers)
    assert balance.json()["ai_match_credits"] == 1  # untouched — no candidate, no charge


@pytest.mark.asyncio
async def test_ai_match_picks_the_higher_compatibility_candidate(client):
    import uuid as uuid_mod

    from app.database import async_session_factory
    from app.models.profile import Profile

    user_id, headers = await create_user_with_profile(client, "aimatchA@example.com", gender="male", interested_in="female")
    async with async_session_factory() as session:
        profile = await session.get(Profile, uuid_mod.UUID(user_id))
        profile.ai_match_credits = 1
        profile.k_content_tags = "bts,blackpink"
        profile.interests = "hiking,coffee"
        await session.commit()

    # Low-overlap candidate joins first (would win on plain FIFO).
    low_id, low_headers = await create_user_with_profile(
        client, "aimatchLow@example.com", gender="female", interested_in="male"
    )
    await client.post("/blind-chat/queue", headers=low_headers, json={"categories": ["travel"]})

    # High-overlap candidate joins second — AI match should still prefer it.
    high_id, high_headers = await create_user_with_profile(
        client, "aimatchHigh@example.com", gender="female", interested_in="male"
    )
    async with async_session_factory() as session:
        high_profile = await session.get(Profile, uuid_mod.UUID(high_id))
        high_profile.k_content_tags = "bts,blackpink"
        high_profile.interests = "hiking,coffee"
        await session.commit()
    await client.post("/blind-chat/queue", headers=high_headers, json={"categories": ["travel"]})

    resp = await client.post("/blind-chat/ai-match", headers=headers, json={"categories": ["travel"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True

    balance = await client.get("/payments/balance", headers=headers)
    assert balance.json()["ai_match_credits"] == 0

    # Confirm it paired with the high-overlap candidate, not the FIFO-first one.
    high_view = await client.get("/blind-chat/queue", headers=high_headers)
    assert high_view.json()["status"] == "matched"
    low_view = await client.get("/blind-chat/queue", headers=low_headers)
    assert low_view.json()["status"] == "waiting"


async def _set_profile(user_id: str, **fields):
    import uuid as uuid_mod

    from app.database import async_session_factory
    from app.models.profile import Profile

    async with async_session_factory() as session:
        profile = await session.get(Profile, uuid_mod.UUID(user_id))
        for name, value in fields.items():
            setattr(profile, name, value)
        await session.commit()


@pytest.mark.asyncio
async def test_regular_queue_matching_ignores_mbti(client):
    # Both ENTP (ENTP is only "compatible" with INTJ) and one even opts into
    # the retired "mbti_match" category — regular matching must not care.
    a_id, a_headers = await create_user_with_profile(client, "mbtiIgnoreA@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "mbtiIgnoreB@example.com", gender="female", interested_in="male")
    await _set_profile(a_id, mbti="ENTP")
    await _set_profile(b_id, mbti="ENTP")

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel", "mbti_match"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel", "mbti_match"]})
    assert r.json()["status"] == "matched"


@pytest.mark.asyncio
async def test_session_gender_choice_overrides_profile_interest(client):
    # Both profiles say "interested in female", but both chose "male" on the
    # match screen for this session — the match-time choice wins, so they pair.
    _, a_headers = await create_user_with_profile(client, "sessionWinsA@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "sessionWinsB@example.com", gender="male", interested_in="female")

    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"], "gender": "male"})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel"], "gender": "male"})
    assert r.json()["status"] == "matched"


@pytest.mark.asyncio
async def test_ai_match_follows_the_gender_chosen_at_match_time(client):
    user_id, headers = await create_user_with_profile(client, "aiGenderA@example.com", gender="male", interested_in="female")
    await _set_profile(user_id, ai_match_credits=1)
    _, cand_headers = await create_user_with_profile(client, "aiGenderB@example.com", gender="male", interested_in="male")
    await client.post("/blind-chat/queue", headers=cand_headers, json={"categories": ["travel"], "gender": "male"})

    # Profile default (female) excludes the waiting male candidate...
    none = await client.post("/blind-chat/ai-match", headers=headers, json={"categories": ["travel"]})
    assert none.json()["found"] is False

    # ...but choosing male on the match screen for this AI match finds them.
    found = await client.post("/blind-chat/ai-match", headers=headers, json={"categories": ["travel"], "gender": "male"})
    assert found.json()["found"] is True
    balance = await client.get("/payments/balance", headers=headers)
    assert balance.json()["ai_match_credits"] == 0


@pytest.mark.asyncio
async def test_ai_match_prefers_the_mbti_compatible_candidate(client):
    user_id, headers = await create_user_with_profile(client, "aiMbtiA@example.com", gender="male", interested_in="female")
    await _set_profile(user_id, ai_match_credits=1, mbti="INTJ")

    # Joins first (would win on plain FIFO) but isn't INTJ's compatible type.
    other_id, other_headers = await create_user_with_profile(
        client, "aiMbtiOther@example.com", gender="female", interested_in="male"
    )
    await _set_profile(other_id, mbti="ISFP")
    await client.post("/blind-chat/queue", headers=other_headers, json={"categories": ["travel"]})

    # Joins second, ENTP = INTJ's single best-match type.
    compat_id, compat_headers = await create_user_with_profile(
        client, "aiMbtiCompat@example.com", gender="female", interested_in="male"
    )
    await _set_profile(compat_id, mbti="ENTP")
    await client.post("/blind-chat/queue", headers=compat_headers, json={"categories": ["travel"]})

    resp = await client.post("/blind-chat/ai-match", headers=headers, json={"categories": ["travel"]})
    assert resp.json()["found"] is True

    assert (await client.get("/blind-chat/queue", headers=compat_headers)).json()["status"] == "matched"
    assert (await client.get("/blind-chat/queue", headers=other_headers)).json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_blind_feedback_submit_then_resubmit_upserts(client):
    _, a_headers, _, _, match_id = await _paired_couple(client, "fbA", "fbB")

    first = await client.post(
        f"/matches/{match_id}/blind-feedback",
        headers=a_headers,
        json={"rating": 3, "tags": ["kind"]},
    )
    assert first.status_code == 200
    body = first.json()
    assert body["rating"] == 3
    assert body["tags"] == ["kind"]
    assert body["comment"] is None

    # A changes their mind — same (match, rater) upserts instead of stacking
    # a second row (the unique constraint on MatchId+RaterUserId).
    second = await client.post(
        f"/matches/{match_id}/blind-feedback",
        headers=a_headers,
        json={
            "rating": 5,
            "tags": ["great_conversation", "other"],
            "comment": "Had a lot in common!",
        },
    )
    assert second.status_code == 200
    body2 = second.json()
    assert body2["rating"] == 5
    assert set(body2["tags"]) == {"great_conversation", "other"}
    assert body2["comment"] == "Had a lot in common!"


@pytest.mark.asyncio
async def test_blind_feedback_comment_requires_other_tag(client):
    _, a_headers, _, _, match_id = await _paired_couple(client, "fbC", "fbD")

    resp = await client.post(
        f"/matches/{match_id}/blind-feedback",
        headers=a_headers,
        json={"rating": 4, "tags": ["kind"], "comment": "not allowed without other"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_blind_feedback_rejects_unknown_tag(client):
    _, a_headers, _, _, match_id = await _paired_couple(client, "fbE", "fbF")

    resp = await client.post(
        f"/matches/{match_id}/blind-feedback",
        headers=a_headers,
        json={"rating": 4, "tags": ["made_up_tag"]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_blind_feedback_rejects_non_participant(client):
    _, _, _, _, match_id = await _paired_couple(client, "fbG", "fbH")
    _, stranger_headers = await create_user_with_profile(client, "fbStranger@example.com")

    resp = await client.post(
        f"/matches/{match_id}/blind-feedback",
        headers=stranger_headers,
        json={"rating": 4, "tags": []},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_blind_feedback_rejects_non_blind_match(client):
    a_id, a_headers = await create_user_with_profile(
        client, "fbSwipeA@example.com", gender="male", interested_in="female"
    )
    b_id, b_headers = await create_user_with_profile(
        client, "fbSwipeB@example.com", gender="female", interested_in="male"
    )
    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    matched = await client.post(
        "/interactions/superlike", headers=b_headers, json={"to_user_id": a_id}
    )
    match_id = matched.json()["match_id"]

    resp = await client.post(
        f"/matches/{match_id}/blind-feedback", headers=a_headers, json={"rating": 4, "tags": []}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_feedback_summary_aggregates_rating_and_tags(client):
    """get_feedback_summary is what llm_match_service folds into its
    ranking prompt — proves the aggregate (not the raw rows/comment) is
    computed correctly for the rated side."""
    import uuid as uuid_mod

    from app.database import async_session_factory
    from app.services import blind_chat_service

    _, a_headers, b_id, _, match_id = await _paired_couple(client, "fbSumA", "fbSumB")
    await client.post(
        f"/matches/{match_id}/blind-feedback",
        headers=a_headers,
        json={"rating": 5, "tags": ["kind", "great_conversation"]},
    )

    async with async_session_factory() as session:
        avg_rating, top_tags = await blind_chat_service.get_feedback_summary(
            session, uuid_mod.UUID(b_id)
        )
    assert avg_rating == 5.0
    assert set(top_tags) == {"kind", "great_conversation"}


@pytest.mark.asyncio
async def test_ai_match_unconfigured_llm_falls_back_to_deterministic_pick(client):
    """No ANTHROPIC_API_KEY is set in this test environment — proves
    find_ai_match's LLM re-ranking step is a true no-op in that case rather
    than erroring the whole request out (llm_match_service.pick_best_candidate
    returns None whenever settings.anthropic_api_key is empty)."""
    import uuid as uuid_mod

    from app.database import async_session_factory
    from app.models.profile import Profile

    user_id, headers = await create_user_with_profile(
        client, "fbLlmA@example.com", gender="male", interested_in="female"
    )
    async with async_session_factory() as session:
        profile = await session.get(Profile, uuid_mod.UUID(user_id))
        profile.ai_match_credits = 1
        await session.commit()

    _, cand_headers = await create_user_with_profile(
        client, "fbLlmB@example.com", gender="female", interested_in="male"
    )
    await client.post("/blind-chat/queue", headers=cand_headers, json={"categories": ["travel"]})

    resp = await client.post(
        "/blind-chat/ai-match", headers=headers, json={"categories": ["travel"]}
    )
    assert resp.status_code == 200
    assert resp.json()["found"] is True
