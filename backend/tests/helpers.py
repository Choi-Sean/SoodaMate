import uuid
from datetime import date

from sqlalchemy import delete

from app.database import async_session_factory
from app.models.interaction import Block, Match, Report, Swipe
from app.models.user import User

_tracked_user_ids: list[str] = []


def track_test_user(user_id: str) -> str:
    """Records a user id a test created so it gets deleted for real once the
    test ends (see conftest.py's _cleanup_real_writes) — there's only one
    database (the user's live hosted MSSQL instance) and it now backs a
    production app under active Play Store review, so tests write to it for
    real and must clean up after themselves rather than relying on a
    schema wipe or a rolled-back transaction. Returns user_id unchanged so
    callers can wrap it inline."""
    _tracked_user_ids.append(user_id)
    return user_id


async def cleanup_tracked_test_users() -> None:
    if not _tracked_user_ids:
        return
    ids = [uuid.UUID(u) for u in _tracked_user_ids]
    _tracked_user_ids.clear()
    async with async_session_factory() as session:
        # Matches/Swipes/Blocks/Reports have no ON DELETE CASCADE from Users
        # (MSSQL disallows a second cascade path to the same table — see
        # app/models/interaction.py), so they must be deleted first;
        # Messages/CallSessions cascade from Matches, and
        # Profiles/Photos/AuthProviders/Verifications/PushTokens/
        # PaymentTransactions cascade from Users.
        await session.execute(delete(Match).where(Match.user_a_id.in_(ids) | Match.user_b_id.in_(ids)))
        await session.execute(delete(Swipe).where(Swipe.from_user_id.in_(ids) | Swipe.to_user_id.in_(ids)))
        await session.execute(delete(Block).where(Block.blocker_id.in_(ids) | Block.blocked_id.in_(ids)))
        await session.execute(delete(Report).where(Report.reporter_id.in_(ids) | Report.reported_id.in_(ids)))
        await session.execute(delete(User).where(User.id.in_(ids)))
        await session.commit()


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
    height_cm: int | None = None,
    exercise_frequency: str | None = None,
) -> tuple[str, dict]:
    """Signs up, completes a profile, returns (user_id, auth_headers)."""
    signup = await client.post("/auth/signup", json={"email": email, "password": "password123"})
    tokens = signup.json()
    track_test_user(tokens["user_id"])
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
            "height_cm": height_cm,
            "exercise_frequency": exercise_frequency,
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
