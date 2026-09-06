from datetime import date


async def create_user_with_profile(
    client,
    email: str,
    *,
    display_name: str = "Test User",
    age: int = 25,
    gender: str = "male",
    interested_in: str = "female",
    min_age_pref: int = 18,
    max_age_pref: int = 99,
    location_lat: float | None = None,
    location_lng: float | None = None,
    race_ethnicity: str | None = None,
    religion: str | None = None,
) -> tuple[str, dict]:
    """Signs up, completes a profile, returns (user_id, auth_headers)."""
    signup = await client.post("/auth/signup", json={"email": email, "password": "password123"})
    tokens = signup.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    birth_year = date.today().year - age
    resp = await client.put(
        "/profiles/me",
        headers=headers,
        json={
            "display_name": display_name,
            "legal_first_name": display_name,
            "birth_date": f"{birth_year}-01-01",
            "gender": gender,
            "interested_in": interested_in,
            "min_age_pref": min_age_pref,
            "max_age_pref": max_age_pref,
            "location_lat": location_lat,
            "location_lng": location_lng,
            "race_ethnicity": race_ethnicity,
            "religion": religion,
        },
    )
    assert resp.status_code == 200, resp.text

    # Give the profile a photo so is_profile_complete flips true and it's discoverable.
    photo_resp = await client.post(
        "/profiles/me/photos/confirm",
        headers=headers,
        json={"gcs_object_path": f"users/{tokens['user_id']}/photos/0.jpg", "position": 0},
    )
    assert photo_resp.status_code == 201, photo_resp.text

    return tokens["user_id"], headers
