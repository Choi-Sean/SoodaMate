import uuid as uuid_mod

import pytest

from tests.helpers import create_ordinary_match, create_user_with_profile

pytestmark = pytest.mark.asyncio


async def _grant_peek_credits(user_id: str, count: int) -> None:
    """Grants `count` purchased credits and deliberately exhausts the
    gender-neutral free daily allowance (reset_at pushed a day out) so these
    credit-focused tests aren't accidentally covered by the free peek
    instead — isolates what's actually being tested."""
    from datetime import datetime, timedelta, timezone

    from app.database import async_session_factory
    from app.models.profile import Profile

    async with async_session_factory() as session:
        profile = await session.get(Profile, uuid_mod.UUID(user_id))
        profile.stealth_peek_credits = count
        profile.free_peek_remaining = 0
        profile.free_peek_reset_at = datetime.now(timezone.utc) + timedelta(days=1)
        await session.commit()


async def _pair_via_blind_chat(client, a_headers, b_headers) -> str:
    await client.post("/blind-chat/queue", headers=a_headers, json={"categories": ["travel"]})
    r = await client.post("/blind-chat/queue", headers=b_headers, json={"categories": ["travel"]})
    assert r.json()["status"] == "matched"
    # The real app's BlindChatQueueScreen polls GET /blind-chat/queue every
    # 3s while waiting, which is what actually clears `a`'s now-matched
    # queue entry (see blind_chat_service.get_queue_status/_resolve_own_entry)
    # — without this, a leftover matched-but-unconsumed entry would make a's
    # *next* queue join resolve to this same old match instead of searching
    # fresh, if this helper is called again reusing the same `a_headers`.
    await client.get("/blind-chat/queue", headers=a_headers)
    return r.json()["match_id"]


async def test_peeking_reveals_real_profile_to_buyer_but_leaves_peer_fully_masked(client):
    a_id, a_headers = await create_user_with_profile(
        client, "peekA1@example.com", display_name="Ahyeon", gender="male", interested_in="female"
    )
    b_id, b_headers = await create_user_with_profile(
        client, "peekB1@example.com", display_name="Bora", gender="female", interested_in="male"
    )
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)
    await _grant_peek_credits(a_id, 1)

    peek_resp = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert peek_resp.status_code == 200
    peeked = peek_resp.json()
    assert peeked["has_peeked"] is True
    assert peeked["other_display_name"] == "Bora"  # real name, not "B***"
    assert peeked["blind_revealed"] is False  # never flips the shared flag

    # The peeker can now also reach the full profile endpoint (previously 403).
    profile_resp = await client.get(f"/matches/{match_id}/profile", headers=a_headers)
    assert profile_resp.status_code == 200
    assert profile_resp.json()["display_name"] == "Bora"

    # 1 credit was actually spent.
    my_profile = (await client.get("/profiles/me", headers=a_headers)).json()
    assert my_profile["stealth_peek_credits"] == 0

    # The peer's own view is completely unaffected: still masked, no
    # has_peeked flag, no reveal, and the full-profile endpoint still 403s.
    b_matches = (await client.get("/matches", headers=b_headers)).json()
    b_view = next(m for m in b_matches if m["id"] == match_id)
    assert b_view["has_peeked"] is False
    assert b_view["blind_revealed"] is False
    assert b_view["other_display_name"].endswith("***")
    assert b_view["other_display_name"] != "Ahyeon"

    b_profile_resp = await client.get(f"/matches/{match_id}/profile", headers=b_headers)
    assert b_profile_resp.status_code == 403


async def test_peeking_twice_does_not_spend_a_second_credit(client):
    a_id, a_headers = await create_user_with_profile(client, "peekA2@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "peekB2@example.com", gender="female", interested_in="male")
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)
    await _grant_peek_credits(a_id, 2)

    r1 = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert r1.status_code == 200
    r2 = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert r2.status_code == 200
    assert r2.json()["has_peeked"] is True

    my_profile = (await client.get("/profiles/me", headers=a_headers)).json()
    assert my_profile["stealth_peek_credits"] == 1  # only the first call charged


async def test_peeking_without_credits_returns_402(client):
    a_id, a_headers = await create_user_with_profile(client, "peekA3@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "peekB3@example.com", gender="female", interested_in="male")
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)
    # Exhaust the gender-neutral free daily allowance too — this test is
    # specifically about having nothing left on either balance.
    await _grant_peek_credits(a_id, 0)

    resp = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert resp.status_code == 402


async def test_cannot_peek_a_non_blind_match(client):
    a_id, a_headers = await create_user_with_profile(client, "peekA4@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "peekB4@example.com", gender="female", interested_in="male")
    await _grant_peek_credits(a_id, 1)

    match_id = await create_ordinary_match(a_id, b_id)

    resp = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert resp.status_code == 400
    # Credit is untouched — nothing was spent on a request that never peeked anything.
    my_profile = (await client.get("/profiles/me", headers=a_headers)).json()
    assert my_profile["stealth_peek_credits"] == 1


async def test_cannot_peek_an_already_revealed_blind_match(client):
    a_id, a_headers = await create_user_with_profile(client, "peekA5@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "peekB5@example.com", gender="female", interested_in="male")
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)
    await _grant_peek_credits(a_id, 1)

    # Mutual reveal, same flow test_blind_chat.py uses elsewhere.
    matches = (await client.get("/matches", headers=a_headers)).json()
    eligible_headers = a_headers if next(m for m in matches if m["id"] == match_id)["can_request_reveal"] else b_headers
    other_headers = b_headers if eligible_headers is a_headers else a_headers
    await client.post(f"/matches/{match_id}/blind-reveal/request", headers=eligible_headers)
    await client.post(f"/matches/{match_id}/blind-reveal/accept", headers=other_headers)

    resp = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert resp.status_code == 400  # already fully revealed — nothing left to peek
    my_profile = (await client.get("/profiles/me", headers=a_headers)).json()
    assert my_profile["stealth_peek_credits"] == 1  # untouched


async def test_peek_by_non_participant_returns_404(client):
    _, a_headers = await create_user_with_profile(client, "peekA6@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "peekB6@example.com", gender="female", interested_in="male")
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)

    stranger_id, stranger_headers = await create_user_with_profile(
        client, "peekStranger6@example.com", gender="male", interested_in="female"
    )
    await _grant_peek_credits(stranger_id, 1)

    resp = await client.post(f"/matches/{match_id}/blind-peek", headers=stranger_headers)
    assert resp.status_code == 404


async def test_peeker_uses_a_free_daily_credit_before_any_purchased_one(client):
    a_id, a_headers = await create_user_with_profile(
        client, "peekFreeA1@example.com", gender="female", interested_in="male"
    )
    _, b_headers = await create_user_with_profile(client, "peekFreeB1@example.com", gender="male", interested_in="female")
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)
    # Deliberately no credits granted and no free-peek state seeded — the
    # very first peek for a brand-new profile must still work for free.

    resp = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert resp.status_code == 200
    assert resp.json()["has_peeked"] is True

    my_profile = (await client.get("/profiles/me", headers=a_headers)).json()
    assert my_profile["stealth_peek_credits"] == 0  # untouched — the free one was spent
    assert my_profile["free_peek_remaining"] == 0  # 1 - 1


async def test_male_also_gets_a_free_daily_peek(client):
    a_id, a_headers = await create_user_with_profile(client, "peekFreeA2@example.com", gender="male", interested_in="female")
    _, b_headers = await create_user_with_profile(client, "peekFreeB2@example.com", gender="female", interested_in="male")
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)

    my_profile = (await client.get("/profiles/me", headers=a_headers)).json()
    assert my_profile["free_peek_remaining"] == 1  # gender-neutral allowance

    resp = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert resp.status_code == 200  # covered by the free daily allowance


async def test_free_peek_allowance_falls_back_to_purchased_credits_once_exhausted(client):
    import uuid as _uuid
    from datetime import datetime, timedelta, timezone

    from app.database import async_session_factory
    from app.models.profile import Profile

    a_id, a_headers = await create_user_with_profile(
        client, "peekFreeA3@example.com", gender="female", interested_in="male"
    )
    b1_id, b1_headers = await create_user_with_profile(client, "peekFreeB3@example.com", gender="male", interested_in="female")
    b2_id, b2_headers = await create_user_with_profile(client, "peekFreeB4@example.com", gender="male", interested_in="female")

    # Already spent today's free peek (reset_at pushed a day out, not NULL —
    # NULL reads as "never granted yet", which would refill immediately and
    # defeat the point of this test), and top up 1 purchased credit.
    async with async_session_factory() as session:
        profile = await session.get(Profile, _uuid.UUID(a_id))
        profile.free_peek_remaining = 0
        profile.free_peek_reset_at = datetime.now(timezone.utc) + timedelta(days=1)
        profile.stealth_peek_credits = 1
        await session.commit()

    match_1 = await _pair_via_blind_chat(client, a_headers, b1_headers)
    r1 = await client.post(f"/matches/{match_1}/blind-peek", headers=a_headers)
    assert r1.status_code == 200  # free allowance is gone, but the purchased credit covers it
    after_paid = (await client.get("/profiles/me", headers=a_headers)).json()
    assert after_paid["stealth_peek_credits"] == 0
    assert after_paid["free_peek_remaining"] == 0

    # A second peek with nothing left on either side 402s.
    match_2 = await _pair_via_blind_chat(client, a_headers, b2_headers)
    r2 = await client.post(f"/matches/{match_2}/blind-peek", headers=a_headers)
    assert r2.status_code == 402


async def test_free_peek_allowance_refills_after_the_daily_window_elapses(client):
    import uuid as _uuid
    from datetime import datetime, timedelta, timezone

    from app.database import async_session_factory
    from app.models.profile import Profile

    a_id, a_headers = await create_user_with_profile(
        client, "peekFreeA5@example.com", gender="female", interested_in="male"
    )
    _, b_headers = await create_user_with_profile(client, "peekFreeB5@example.com", gender="male", interested_in="female")
    match_id = await _pair_via_blind_chat(client, a_headers, b_headers)

    # Exhausted allowance whose window already elapsed — a real "used it,
    # then 24+ hours went by" state, backdated directly (no scheduler exists
    # to advance a day for real, same convention test_blind_chat.py's
    # unlimited-matching test uses).
    async with async_session_factory() as session:
        profile = await session.get(Profile, _uuid.UUID(a_id))
        profile.free_peek_remaining = 0
        profile.free_peek_reset_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await session.commit()

    # Even before spending one, GET /profiles/me should already show the
    # refreshed count (read-only recompute — see routers/profiles.py).
    before_spend = (await client.get("/profiles/me", headers=a_headers)).json()
    assert before_spend["free_peek_remaining"] == 1

    resp = await client.post(f"/matches/{match_id}/blind-peek", headers=a_headers)
    assert resp.status_code == 200
    after_spend = (await client.get("/profiles/me", headers=a_headers)).json()
    assert after_spend["free_peek_remaining"] == 0
    assert after_spend["stealth_peek_credits"] == 0
