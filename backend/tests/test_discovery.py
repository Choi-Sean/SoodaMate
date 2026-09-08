import pytest

from tests.helpers import create_user_with_profile


async def _disable_expand(client, headers, max_distance_km: int = 500):
    """expand_distance_if_low/expand_others_if_low default True on the real
    API (matching Bumble's own default-on toggles - see
    discovery_service.get_candidates) - tests that assert a strict
    exclusion need both off, or a too-small candidate pool gets backfilled
    with exactly the candidate the test is trying to prove got excluded.
    max_distance_km is a required field on this same PUT (full-replace, not
    a patch) - pass the caller's intended value or it silently resets to
    the schema default."""
    resp = await client.put(
        "/profiles/me/basic-filters",
        headers=headers,
        json={"max_distance_km": max_distance_km, "expand_distance_if_low": False, "expand_others_if_low": False},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_matching_gender_candidate_appears(client):
    _, viewer_headers = await create_user_with_profile(
        client, "viewer@example.com", gender="male", interested_in="female"
    )
    candidate_id, _ = await create_user_with_profile(
        client, "candidate@example.com", gender="female", interested_in="male"
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    assert resp.status_code == 200
    ids = [c["user_id"] for c in resp.json()]
    assert candidate_id in ids


@pytest.mark.asyncio
async def test_candidate_bio2_and_bio3_are_visible_to_other_users(client):
    """Regression test: bio2/bio3 were added to Profile/ProfileOut (so a
    user could set them on their own profile) but CandidateOut/
    _to_candidates_out were never updated to also serialize them - the
    fields saved but silently never reached anyone else's Discover/Swipe
    feed."""
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "viewer_bio23@example.com", gender="male", interested_in="female"
    )
    candidate_id, candidate_headers = await create_user_with_profile(
        client, "candidate_bio23@example.com", gender="female", interested_in="male"
    )
    resp = await client.put(
        "/profiles/me",
        headers=candidate_headers,
        json={
            "display_name": "Test User",
            "legal_first_name": "Test User",
            "birth_date": "1999-01-01",
            "gender": "female",
            "interested_in": "male",
            "bio2": "More about me",
            "bio3": "One more thing",
        },
    )
    assert resp.status_code == 200

    candidates = await client.get("/discovery/candidates", headers=viewer_headers)
    candidate = next(c for c in candidates.json() if c["user_id"] == candidate_id)
    assert candidate["bio2"] == "More about me"
    assert candidate["bio3"] == "One more thing"


@pytest.mark.asyncio
async def test_non_matching_gender_preference_excluded(client):
    _, viewer_headers = await create_user_with_profile(
        client, "viewer2@example.com", gender="male", interested_in="female"
    )
    # This candidate is only interested in females, not males -> not mutual.
    other_id, _ = await create_user_with_profile(
        client, "other2@example.com", gender="female", interested_in="female"
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert other_id not in ids


@pytest.mark.asyncio
async def test_age_out_of_range_excluded(client):
    _, viewer_headers = await create_user_with_profile(
        client,
        "viewer3@example.com",
        gender="male",
        interested_in="female",
        min_age_pref=18,
        max_age_pref=25,
    )
    await _disable_expand(client, viewer_headers)
    too_old_id, _ = await create_user_with_profile(
        client, "old3@example.com", gender="female", interested_in="male", age=40
    )
    in_range_id, _ = await create_user_with_profile(
        client, "young3@example.com", gender="female", interested_in="male", age=22
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert too_old_id not in ids
    assert in_range_id in ids


@pytest.mark.asyncio
async def test_already_swiped_excluded_from_future_candidates(client):
    _, viewer_headers = await create_user_with_profile(
        client, "viewer4@example.com", gender="male", interested_in="female"
    )
    candidate_id, _ = await create_user_with_profile(
        client, "candidate4@example.com", gender="female", interested_in="male"
    )

    await client.post(
        "/interactions/pass", headers=viewer_headers, json={"to_user_id": candidate_id}
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert candidate_id not in ids


@pytest.mark.asyncio
async def test_distance_filter_excludes_far_away_candidate(client):
    # Seoul-ish coordinates for the viewer, with a tight 10km radius.
    _, viewer_headers = await create_user_with_profile(
        client,
        "viewer5@example.com",
        gender="male",
        interested_in="female",
        location_lat=37.5665,
        location_lng=126.9780,
    )
    # Override max_distance_km via a second PUT (helper doesn't expose it directly).
    await client.put(
        "/profiles/me",
        headers=viewer_headers,
        json={
            "display_name": "Test User",
            "legal_first_name": "Test User",
            "birth_date": "1999-01-01",
            "gender": "male",
            "interested_in": "female",
            "min_age_pref": 18,
            "max_age_pref": 99,
            "max_distance_km": 10,
            "location_lat": 37.5665,
            "location_lng": 126.9780,
        },
    )
    await _disable_expand(client, viewer_headers, max_distance_km=10)
    # Busan, ~325km away.
    far_id, _ = await create_user_with_profile(
        client,
        "far5@example.com",
        gender="female",
        interested_in="male",
        location_lat=35.1796,
        location_lng=129.0756,
    )
    # A few hundred meters away.
    near_id, _ = await create_user_with_profile(
        client,
        "near5@example.com",
        gender="female",
        interested_in="male",
        location_lat=37.5680,
        location_lng=126.9790,
    )

    resp = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in resp.json()]
    assert far_id not in ids
    assert near_id in ids
