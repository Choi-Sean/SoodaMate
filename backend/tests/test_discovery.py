import pytest

from tests.helpers import create_user_with_profile


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
