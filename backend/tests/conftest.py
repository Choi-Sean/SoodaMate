import asyncio
import os
import sys

import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient, Response

# aioodbc wraps blocking pyodbc calls in a thread executor rather than doing
# raw asyncio socket I/O; unclear whether the loop-mixing crash that made
# this necessary for asyncpg still applies here, but it's a harmless safe
# default either way (kept until proven unnecessary against a live run).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["APP_ENV"] = "test"

# Loads backend/.env's real DATABASE_URL (the user's hosted MSSQL instance —
# there is no separate local/container test database; this project has only
# ever run against one real database, which now also backs the live
# production app). Only override it if TEST_DATABASE_URL is explicitly set
# (e.g. CI pointed at a disposable instance, or a local Docker MSSQL
# container per infra/docker-compose.yml).
load_dotenv()
if "TEST_DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from app.database import engine  # noqa: E402  (must import after env vars are set)
from app.main import app  # noqa: E402
from tests.helpers import cleanup_tracked_test_users, track_test_user  # noqa: E402

# Endpoints that can create a brand-new user (see app/routers/auth.py).
# /login and /refresh never create one, so they're deliberately excluded —
# tracking them could otherwise mark a pre-existing (possibly real) account
# for deletion just because a test happened to log in as it.
_USER_CREATING_PATHS = {"/auth/signup", "/auth/google", "/auth/kakao", "/auth/apple"}


async def _track_created_user(response: Response) -> None:
    if response.request.url.path not in _USER_CREATING_PATHS or response.status_code >= 300:
        return
    await response.aread()
    user_id = response.json().get("user_id")
    if user_id:
        track_test_user(user_id)


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _cleanup_real_writes():
    """
    There is only one database (see the DATABASE_URL note above), and it now
    backs a live production app under active Play Store review, so tests
    must never leave permanent junk in it. This fixture used to
    drop/recreate the *entire schema* before every single test instead
    (`Base.metadata.drop_all` + `create_all`); that really did wipe
    production data — real signups, matches, messages, payments — on every
    local `pytest` run. Removed for exactly that reason.

    A shared-connection/rollback-transaction replacement was tried and
    reverted: MSSQL's SAVEPOINT support over pyodbc/aioodbc, shared across
    the many sessions one test opens, hit real driver errors ("pending
    requests working on this transaction") that a plain `SET NOCOUNT ON`
    workaround just traded for a different one (SQLAlchemy's rowcount-based
    staleness check needs the rowcount NOCOUNT suppresses). Simpler and
    more robust: tests write for real, through the exact same one database
    everything else uses, and whatever user they created gets deleted for
    real afterward. `client`'s response hook above (and
    test_chat_ws.py's `_signup_and_complete_profile`, for the sync-
    TestClient WebSocket/call tests, which can't share this fixture's
    event loop) do the tracking; this just drains it.
    """
    yield
    await cleanup_tracked_test_users()
    # Each test gets a fresh event loop (pytest-asyncio, function scope); the
    # pooled connections must not outlive it or the driver's teardown crashes.
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", event_hooks={"response": [_track_created_user]}
    ) as ac:
        yield ac
