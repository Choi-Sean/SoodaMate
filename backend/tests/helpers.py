import uuid
from datetime import date

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
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


def _throwaway_session_factory():
    """A brand-new engine/pool, entirely separate from app.database.engine —
    used only by the two helpers below. Deliberately NOT the app's shared
    async_session_factory: that engine's async internals get bound to
    whichever event loop first touches it, and create_ordinary_match_sync
    below runs its own throwaway asyncio.run() loop, distinct from both
    pytest-asyncio's per-function loop and Starlette TestClient's own
    background portal loop. Reusing the shared engine across a THIRD loop
    silently deadlocked the *next* test's DB access on the app's real engine
    (confirmed empirically — see app/database.py's own NullPool comment for
    the first, related cross-loop failure mode this test suite already hit).
    A fully separate engine, created and disposed within the same single
    loop it's used in, never touches the shared one at all."""
    engine = create_async_engine(settings.database_url, poolclass=NullPool, deprecate_large_types=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def record_swipe_direct(from_user_id: str, to_user_id: str, action: str) -> dict:
    """Calls match_service.record_swipe directly (bypassing the now-
    discontinued /interactions/like + /superlike HTTP endpoints — see
    routers/interactions.py) for tests that need one single, specific swipe
    action rather than a full mutual match (e.g. exercising GET /discovery/
    liked-me's superliked_me flag). Returns {"matched": bool, "match_id": str|None}."""
    from app.services.match_service import record_swipe

    engine, session_factory = _throwaway_session_factory()
    try:
        async with session_factory() as session:
            result = await record_swipe(session, uuid.UUID(from_user_id), uuid.UUID(to_user_id), action)
    finally:
        await engine.dispose()
    return {"matched": result.matched, "match_id": str(result.match_id) if result.match_id else None}


async def create_ordinary_match(user_a_id: str, user_b_id: str) -> str:
    """Creates a non-blind Match the same real way /interactions/like +
    /interactions/superlike used to (via match_service.record_swipe — the
    actual stored proc and match-creation semantics, not a synthetic DB
    insert), bypassing the HTTP layer directly. Those two endpoints were
    discontinued (see routers/interactions.py) since nothing in the app can
    reach them anymore, but plenty of unrelated tests (chat, video/voice
    call, couple stories, icebreaker, delete-match, ...) still need *a*
    match to test on top of. Two separate sessions, matching the isolation
    the old two-HTTP-request flow had."""
    from app.services.match_service import record_swipe

    engine, session_factory = _throwaway_session_factory()
    try:
        async with session_factory() as session:
            await record_swipe(session, uuid.UUID(user_a_id), uuid.UUID(user_b_id), "like")
        async with session_factory() as session:
            result = await record_swipe(session, uuid.UUID(user_b_id), uuid.UUID(user_a_id), "like")
    finally:
        await engine.dispose()
    return str(result.match_id)


def create_ordinary_match_sync(user_a_id: str, user_b_id: str) -> str:
    """Sync wrapper of create_ordinary_match for the TestClient-based
    (non-httpx, non-pytest-asyncio) test modules — test_chat_ws.py and
    test_video_call.py drive everything through the sync Starlette
    TestClient and have no running event loop of their own to await into.
    Safe specifically because create_ordinary_match never touches the app's
    shared engine (see _throwaway_session_factory's docstring) — this
    asyncio.run() loop is used and torn down without ever crossing into the
    TestClient portal's own separate loop."""
    import asyncio

    return asyncio.run(create_ordinary_match(user_a_id, user_b_id))


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
    education: str | None = None,
    mbti: str | None = None,
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
            "education": education,
            "mbti": mbti,
        },
    )
    assert resp.status_code == 200, resp.text

    # Give the profile a photo so is_profile_complete flips true and it's discoverable.
    photo_resp = await client.post(
        "/profiles/me/photos/confirm",
        headers=headers,
        json={"gcs_object_path": f"users/{tokens['user_id']}/photos/{uuid.uuid4()}.jpg", "position": 0},
    )
    assert photo_resp.status_code == 201, photo_resp.text

    return tokens["user_id"], headers
