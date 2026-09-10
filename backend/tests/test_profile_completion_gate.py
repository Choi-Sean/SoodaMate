import uuid
from datetime import date

import pytest
from sqlalchemy import update

from app.database import async_session_factory
from app.models.profile import Profile
from tests.helpers import track_test_user


async def _signup(client, email):
    r = await client.post("/auth/signup", json={"email": email, "password": "password123"})
    tokens = r.json()
    track_test_user(tokens["user_id"])
    return tokens["user_id"], {"authorization": f"Bearer {tokens['access_token']}"}


def _profile_body(gender="male"):
    by = date.today().year - 27
    return {
        "display_name": "Sam",
        "legal_first_name": "Sam",
        "birth_date": f"{by}-01-01",
        "gender": gender,
        "interested_in": "female",
        "min_age_pref": 18,
        "max_age_pref": 99,
    }


@pytest.mark.asyncio
async def test_profile_without_photo_is_not_complete(client):
    _, headers = await _signup(client, "gate1@example.com")
    r = await client.put("/profiles/me", headers=headers, json=_profile_body())
    assert r.status_code == 200
    assert r.json()["is_profile_complete"] is False  # has core fields but no photo


@pytest.mark.asyncio
async def test_blank_core_field_keeps_profile_incomplete_even_with_a_photo(client):
    uid, headers = await _signup(client, "gate2@example.com")
    await client.put("/profiles/me", headers=headers, json=_profile_body())

    # Simulate a legacy/partial row whose gender was never captured.
    async with async_session_factory() as s:
        await s.execute(update(Profile).where(Profile.user_id == uuid.UUID(uid)).values(gender=""))
        await s.commit()

    photo = await client.post(
        "/profiles/me/photos/confirm",
        headers=headers,
        json={"gcs_object_path": f"users/{uid}/photos/0.jpg", "position": 0},
    )
    assert photo.status_code == 201

    me = await client.get("/profiles/me", headers=headers)
    assert me.json()["is_profile_complete"] is False  # photo present, but gender still blank


@pytest.mark.asyncio
async def test_blank_core_field_is_editable_then_locks_once_set(client):
    uid, headers = await _signup(client, "gate3@example.com")
    await client.put("/profiles/me", headers=headers, json=_profile_body(gender="male"))

    async with async_session_factory() as s:
        await s.execute(update(Profile).where(Profile.user_id == uuid.UUID(uid)).values(gender=""))
        await s.commit()

    # Blank -> the incoming value is accepted.
    r1 = await client.put("/profiles/me", headers=headers, json=_profile_body(gender="female"))
    assert r1.json()["gender"] == "female"

    # Now set -> locked; a later change is ignored, the stored value wins.
    r2 = await client.put("/profiles/me", headers=headers, json=_profile_body(gender="male"))
    assert r2.json()["gender"] == "female"


@pytest.mark.asyncio
async def test_set_core_fields_stay_locked(client):
    uid, headers = await _signup(client, "gate4@example.com")
    await client.put("/profiles/me", headers=headers, json=_profile_body(gender="male"))

    body = _profile_body(gender="female")
    body["display_name"] = "Changed"
    r = await client.put("/profiles/me", headers=headers, json=body)
    assert r.json()["gender"] == "male"
    assert r.json()["display_name"] == "Sam"
