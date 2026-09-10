import json

import pytest
import stripe

from tests.helpers import create_user_with_profile

_WEBHOOK_SECRET = "whsec_testsecret_0123456789abcdef"


async def _grant_membership(client, monkeypatch, user_id: str, event_id: str = "evt_membership_1"):
    import app.services.payment_service as payment_service

    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)
    event = {
        "id": event_id,
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{event_id}",
                "object": "checkout.session",
                "subscription": f"sub_{event_id}",
                "metadata": {"user_id": user_id, "product_id": "membership_monthly"},
            }
        },
    }
    payload = json.dumps(event)
    sig = stripe.WebhookSignature.generate_signature_header(payload, _WEBHOOK_SECRET)
    resp = await client.post("/payments/webhook", content=payload.encode(), headers={"stripe-signature": sig})
    assert resp.status_code == 204, resp.text


async def _set_basic_filters(client, headers, **overrides):
    """Every field defaults to "off"/permissive except the two expand
    toggles, which default to False here (opposite of the real API
    default) specifically so exclusion assertions in these tests get a
    clean strict result unless a test explicitly wants the fallback."""
    body = {
        "max_distance_km": 500,
        "race_filter": [],
        "height_min": None,
        "height_max": None,
        "languages_filter": [],
        "interests_filter": [],
        "verified_only": False,
        "expand_distance_if_low": False,
        "expand_others_if_low": False,
    }
    body.update(overrides)
    resp = await client.put("/profiles/me/basic-filters", headers=headers, json=body)
    assert resp.status_code == 200
    return resp


@pytest.mark.asyncio
async def test_free_user_cannot_set_premium_filters(client):
    _, headers = await create_user_with_profile(client, "free1@example.com")
    resp = await client.put(
        "/profiles/me/premium-filters",
        headers=headers,
        json={"religion_filter": ["buddhist"]},
    )
    assert resp.status_code == 402


@pytest.mark.asyncio
async def test_membership_purchase_grants_premium(client, monkeypatch):
    user_id, headers = await create_user_with_profile(client, "premium1@example.com")
    await _grant_membership(client, monkeypatch, user_id)

    profile = await client.get("/profiles/me", headers=headers)
    assert profile.json()["is_premium_member"] is True

    resp = await client.put(
        "/profiles/me/premium-filters",
        headers=headers,
        json={"religion_filter": ["buddhist"]},
    )
    assert resp.status_code == 200
    assert resp.json()["religion_filter"] == ["buddhist"]


@pytest.mark.asyncio
async def test_race_filter_is_free_and_excludes_non_matching_candidates(client):
    """race_filter moved out of the premium bucket — no _grant_membership
    here at all, unlike the religion test below."""
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_race@example.com", gender="male", interested_in="female"
    )
    await _set_basic_filters(client, viewer_headers, race_filter=["east_asian"])

    matching_id, _ = await create_user_with_profile(
        client,
        "match_race@example.com",
        gender="female",
        interested_in="male",
        race_ethnicity="east_asian",
    )
    non_matching_id, _ = await create_user_with_profile(
        client,
        "nomatch_race@example.com",
        gender="female",
        interested_in="male",
        race_ethnicity="white",
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert matching_id in ids
    assert non_matching_id not in ids


@pytest.mark.asyncio
async def test_religion_filter_excludes_non_matching_candidates(client, monkeypatch):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_rel@example.com", gender="male", interested_in="female"
    )
    await _grant_membership(client, monkeypatch, viewer_id, event_id="evt_rel_1")
    await _set_basic_filters(client, viewer_headers)
    await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"religion_filter": ["buddhist"]},
    )

    matching_id, _ = await create_user_with_profile(
        client,
        "match_rel@example.com",
        gender="female",
        interested_in="male",
        religion="buddhist",
    )
    non_matching_id, _ = await create_user_with_profile(
        client,
        "nomatch_rel@example.com",
        gender="female",
        interested_in="male",
        religion="christian",
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert matching_id in ids
    assert non_matching_id not in ids


@pytest.mark.asyncio
async def test_expired_membership_stops_applying_religion_filter(client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.database import async_session_factory
    from app.models.profile import Profile

    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_expired@example.com", gender="male", interested_in="female"
    )
    await _grant_membership(client, monkeypatch, viewer_id, event_id="evt_expired_1")
    await _set_basic_filters(client, viewer_headers)
    await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"religion_filter": ["buddhist"]},
    )

    # Backdate premium_until directly — the filter value stays set, only
    # membership status changes, to prove discovery re-checks it at read
    # time rather than trusting whatever was true when the filter was saved.
    async with async_session_factory() as session:
        import uuid

        profile = await session.get(Profile, uuid.UUID(viewer_id))
        profile.premium_until = datetime.now(timezone.utc) - timedelta(days=1)
        await session.commit()

    non_matching_id, _ = await create_user_with_profile(
        client,
        "nomatch_expired@example.com",
        gender="female",
        interested_in="male",
        religion="christian",
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    # Membership lapsed, so the (still-stored) religion_filter must no
    # longer exclude anyone — Advanced filters require an active membership
    # at read time, not just when the filter was set.
    assert non_matching_id in ids


@pytest.mark.asyncio
async def test_free_user_can_set_age_filter(client):
    _, headers = await create_user_with_profile(client, "free_age@example.com")
    resp = await client.put(
        "/profiles/me/age-filter", headers=headers, json={"min_age_pref": 25, "max_age_pref": 35}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["min_age_pref"] == 25
    assert body["max_age_pref"] == 35


@pytest.mark.asyncio
async def test_height_filter_is_free_and_excludes_non_matching_candidates(client):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_height@example.com", gender="male", interested_in="female"
    )
    filter_resp = await _set_basic_filters(client, viewer_headers, height_min=160, height_max=170)
    assert filter_resp.json()["height_filter_min"] == 160
    assert filter_resp.json()["height_filter_max"] == 170

    matching_id, _ = await create_user_with_profile(
        client, "match_height@example.com", gender="female", interested_in="male", height_cm=165
    )
    wrong_height_id, _ = await create_user_with_profile(
        client, "nomatch_height@example.com", gender="female", interested_in="male", height_cm=180
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert matching_id in ids
    assert wrong_height_id not in ids


@pytest.mark.asyncio
async def test_exercise_filter_still_premium_and_excludes_non_matching_candidates(client, monkeypatch):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_exercise@example.com", gender="male", interested_in="female"
    )
    await _grant_membership(client, monkeypatch, viewer_id, event_id="evt_exercise_1")
    await _set_basic_filters(client, viewer_headers)
    filter_resp = await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"exercise_frequency_filter": ["daily"]},
    )
    assert filter_resp.json()["premium_filters"]["exercise_frequency_filter"] == ["daily"]

    matching_id, _ = await create_user_with_profile(
        client, "match_exercise@example.com", gender="female", interested_in="male", exercise_frequency="daily"
    )
    wrong_exercise_id, _ = await create_user_with_profile(
        client, "nomatch_exercise@example.com", gender="female", interested_in="male", exercise_frequency="never"
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert matching_id in ids
    assert wrong_exercise_id not in ids


@pytest.mark.asyncio
async def test_premium_filters_full_replace_clears_omitted_dimensions(client, monkeypatch):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_replace@example.com", gender="male", interested_in="female"
    )
    await _grant_membership(client, monkeypatch, viewer_id, event_id="evt_replace_1")
    await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"exercise_frequency_filter": ["daily"]},
    )
    # A second request that only sets a different dimension is a full
    # replace, not a merge — the earlier exercise filter is gone.
    resp = await client.put(
        "/profiles/me/premium-filters", headers=viewer_headers, json={"smoking_filter": ["never"]}
    )
    assert resp.status_code == 200
    filters = resp.json()["premium_filters"]
    assert filters["smoking_filter"] == ["never"]
    assert filters["exercise_frequency_filter"] == []


@pytest.mark.asyncio
async def test_basic_filters_full_replace_clears_omitted_dimensions(client):
    _, headers = await create_user_with_profile(client, "viewer_basic_replace@example.com")
    await _set_basic_filters(client, headers, race_filter=["east_asian"], height_min=150, height_max=200)
    resp = await _set_basic_filters(client, headers, languages_filter=["english"])
    body = resp.json()
    assert body["languages_filter"] == ["english"]
    assert body["race_filter"] == []
    assert body["height_filter_min"] is None
    assert body["height_filter_max"] is None


@pytest.mark.asyncio
async def test_verified_only_filter_excludes_unverified_candidates(client):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_verified@example.com", gender="male", interested_in="female"
    )
    await _set_basic_filters(client, viewer_headers, verified_only=True)

    unverified_id, _ = await create_user_with_profile(
        client, "unverified@example.com", gender="female", interested_in="male"
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert unverified_id not in ids


@pytest.mark.asyncio
async def test_languages_filter_matches_exact_segment_not_substring(client):
    """_csv_contains_any wraps the stored CSV in commas specifically to
    avoid a language/interest key matching as a substring of another
    stored value — this is the regression test for that."""
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_lang@example.com", gender="male", interested_in="female"
    )
    await _set_basic_filters(client, viewer_headers, languages_filter=["english"])

    matching_id, matching_headers = await create_user_with_profile(
        client, "match_lang@example.com", gender="female", interested_in="male"
    )
    await client.put(
        "/profiles/me", headers=matching_headers, json=_profile_update_with_languages(["english", "korean"])
    )
    non_matching_id, non_matching_headers = await create_user_with_profile(
        client, "nomatch_lang@example.com", gender="female", interested_in="male"
    )
    await client.put(
        "/profiles/me", headers=non_matching_headers, json=_profile_update_with_languages(["korean"])
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert matching_id in ids
    assert non_matching_id not in ids


def _profile_update_with_languages(languages: list[str]) -> dict:
    import datetime

    return {
        "display_name": "Test",
        "legal_first_name": "Test",
        "birth_date": str(datetime.date(1995, 1, 1)),
        "gender": "female",
        "interested_in": "male",
        "languages": languages,
    }


@pytest.mark.asyncio
async def test_expand_others_if_low_backfills_beyond_age_range(client):
    """With expand_others_if_low on (the real API default), an
    age-mismatched candidate is still returned once the strict pool runs
    short — the opposite of every strict-exclusion test above, which
    explicitly turns this toggle off via _set_basic_filters."""
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_expand@example.com", gender="male", interested_in="female"
    )
    await client.put(
        "/profiles/me/age-filter", headers=viewer_headers, json={"min_age_pref": 18, "max_age_pref": 19}
    )
    # expand_others_if_low defaults True — don't call _set_basic_filters
    # (which would turn it off) at all here.

    out_of_range_id, _ = await create_user_with_profile(
        client, "outofrange_expand@example.com", gender="female", interested_in="male"
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert out_of_range_id in ids
