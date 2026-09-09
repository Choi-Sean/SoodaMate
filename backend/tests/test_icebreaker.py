import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_icebreaker_prefers_shared_kcontent_over_interests(client):
    a_id, a_headers = await create_user_with_profile(client, "iceA@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "iceB@example.com", gender="female", interested_in="male")

    await client.put(
        "/profiles/me",
        headers=a_headers,
        json=_profile_body("A", "male", "female", interests=["hiking"], k_content_tags=["newjeans", "squid_game"]),
    )
    await client.put(
        "/profiles/me",
        headers=b_headers,
        json=_profile_body("B", "female", "male", interests=["hiking"], k_content_tags=["newjeans"]),
    )

    like_a = await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    match_resp = await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
    assert match_resp.json()["matched"] is True
    match_id = match_resp.json()["match_id"]

    resp = await client.get(f"/matches/{match_id}/icebreaker", headers=a_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "shared_kcontent"
    assert body["key"] == "newjeans"


@pytest.mark.asyncio
async def test_icebreaker_falls_back_to_generic_with_nothing_shared(client):
    a_id, a_headers = await create_user_with_profile(client, "iceC@example.com", gender="male", interested_in="female")
    b_id, b_headers = await create_user_with_profile(client, "iceD@example.com", gender="female", interested_in="male")

    await client.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
    match_resp = await client.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
    match_id = match_resp.json()["match_id"]

    resp = await client.get(f"/matches/{match_id}/icebreaker", headers=a_headers)
    assert resp.status_code == 200
    assert resp.json()["type"] == "generic"


def _profile_body(name, gender, interested_in, *, interests, k_content_tags):
    from datetime import date

    birth_year = date.today().year - 25
    return {
        "display_name": name,
        "legal_first_name": name,
        "birth_date": f"{birth_year}-01-01",
        "gender": gender,
        "interested_in": interested_in,
        "min_age_pref": 18,
        "max_age_pref": 99,
        "interests": interests,
        "k_content_tags": k_content_tags,
    }
