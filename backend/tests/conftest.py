import asyncio
import os
import sys

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

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
# ever run against one real database). Only override it if TEST_DATABASE_URL
# is explicitly set (e.g. CI pointed at a disposable instance).
load_dotenv()
if "TEST_DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from app.database import Base, engine  # noqa: E402  (must import after env vars are set)
from app.main import app  # noqa: E402


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _reset_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Each test gets a fresh event loop (pytest-asyncio, function scope); the
    # pooled connections must not outlive it or the driver's teardown crashes.
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
