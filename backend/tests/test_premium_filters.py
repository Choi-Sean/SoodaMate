import pytest

from tests.helpers import create_user_with_profile


async def _grant_membership(client, monkeypatch, user_id: str, event_id: str = "evt_membership_1"):
    import app.services.payment_service as payment_service

    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", "whsec_fake")
    fake_event = {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{event_id}",
                "metadata": {"user_id": user_id, "product_id": "membership_30d"},
            }
        },
    }
    monkeypatch.setattr(payment_service.stripe.Webhook, "construct_event", lambda *a, **kw: fake_event)
    resp = await client.post("/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"})
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_free_user_cannot_set_premium_filters(client):
    _, headers = await create_user_with_profile(client, "free1@example.com")
    resp = await client.put(
        "/profiles/me/premium-filters",
        headers=headers,
        json={"race_filter": ["east_asian"], "religion_filter": []},
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
        json={"race_filter": ["east_asian"], "religion_filter": []},
    )
    assert resp.status_code == 200
    assert resp.json()["race_filter"] == ["east_asian"]


@pytest.mark.asyncio
async def test_race_filter_excludes_non_matching_candidates(client, monkeypatch):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_race@example.com", gender="male", interested_in="female"
    )
    await _grant_membership(client, monkeypatch, viewer_id, event_id="evt_race_1")
    await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"race_filter": ["east_asian"], "religion_filter": []},
    )

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
    await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"race_filter": [], "religion_filter": ["buddhist"]},
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
async def test_expired_membership_stops_applying_filter(client, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.database import async_session_factory
    from app.models.profile import Profile

    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_expired@example.com", gender="male", interested_in="female"
    )
    await _grant_membership(client, monkeypatch, viewer_id, event_id="evt_expired_1")
    await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"race_filter": ["east_asian"], "religion_filter": []},
    )

    # Backdate premium_until directly — the filter values stay set, only
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
        race_ethnicity="white",
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    # Membership lapsed, so the (still-stored) race_filter must no longer
    # exclude anyone — the free tier only ever gets age/distance filtering.
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
async def test_height_and_exercise_filter_exclude_non_matching_candidates(client, monkeypatch):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_height@example.com", gender="male", interested_in="female"
    )
    await _grant_membership(client, monkeypatch, viewer_id, event_id="evt_height_1")
    filter_resp = await client.put(
        "/profiles/me/premium-filters",
        headers=viewer_headers,
        json={"height_min": 160, "height_max": 170, "exercise_frequency_filter": ["daily"]},
    )
    assert filter_resp.status_code == 200
    assert filter_resp.json()["premium_filters"]["height_min"] == 160
    assert filter_resp.json()["premium_filters"]["exercise_frequency_filter"] == ["daily"]

    matching_id, _ = await create_user_with_profile(
        client,
        "match_height@example.com",
        gender="female",
        interested_in="male",
        height_cm=165,
        exercise_frequency="daily",
    )
    wrong_height_id, _ = await create_user_with_profile(
        client,
        "nomatch_height@example.com",
        gender="female",
        interested_in="male",
        height_cm=180,
        exercise_frequency="daily",
    )
    wrong_exercise_id, _ = await create_user_with_profile(
        client,
        "nomatch_exercise@example.com",
        gender="female",
        interested_in="male",
        height_cm=165,
        exercise_frequency="never",
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert matching_id in ids
    assert wrong_height_id not in ids
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
        json={"exercise_frequency_filter": ["daily"], "height_min": 150},
    )
    # A second request that only sets a different dimension is a full
    # replace, not a merge — the earlier exercise/height filters are gone.
    resp = await client.put(
        "/profiles/me/premium-filters", headers=viewer_headers, json={"smoking_filter": ["never"]}
    )
    assert resp.status_code == 200
    filters = resp.json()["premium_filters"]
    assert filters["smoking_filter"] == ["never"]
    assert filters["exercise_frequency_filter"] == []
    assert filters["height_min"] is None
