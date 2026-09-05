import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_incognito_hides_from_discovery(client):
    viewer_id, viewer_headers = await create_user_with_profile(
        client, "inctv1@example.com", gender="male", interested_in="female"
    )
    hidden_id, hidden_headers = await create_user_with_profile(
        client, "inctv2@example.com", gender="female", interested_in="male"
    )

    resp = await client.post("/profiles/me/incognito", headers=hidden_headers, json={"is_incognito": True})
    assert resp.status_code == 200
    assert resp.json()["is_incognito"] is True

    candidates = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in candidates.json()]
    assert hidden_id not in ids


@pytest.mark.asyncio
async def test_travel_mode_repositions_for_distance_filter(client):
    viewer_id, viewer_headers = await create_user_with_profile(
        client,
        "inctv3@example.com",
        gender="male",
        interested_in="female",
        location_lat=37.5665,
        location_lng=126.9780,
    )
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
    # Candidate is physically far away (Busan) but activates travel mode to
    # Seoul coordinates — should become visible under the 10km filter.
    far_id, far_headers = await create_user_with_profile(
        client,
        "inctv4@example.com",
        gender="female",
        interested_in="male",
        location_lat=35.1796,
        location_lng=129.0756,
    )
    travel_resp = await client.post(
        "/profiles/me/travel", headers=far_headers, json={"lat": 37.5680, "lng": 126.9790, "duration_hours": 24}
    )
    assert travel_resp.status_code == 200
    assert travel_resp.json()["travel_lat"] == 37.5680

    candidates = await client.get("/discovery/candidates", headers=viewer_headers)
    ids = [c["user_id"] for c in candidates.json()]
    assert far_id in ids

    clear_resp = await client.delete("/profiles/me/travel", headers=far_headers)
    assert clear_resp.status_code == 200
    assert clear_resp.json()["travel_lat"] is None
