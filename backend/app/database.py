from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# deprecate_large_types: MSSQL-only engine option so Text/UnicodeText columns
# compile to modern NVARCHAR(MAX) instead of the legacy NTEXT type.
_engine_kwargs = {"deprecate_large_types": True}

if settings.app_env == "test":
    # Tests mix pytest-asyncio's per-function loop with Starlette TestClient's
    # own background-thread loop (for WebSocket tests). aioodbc wraps
    # blocking pyodbc calls in a thread executor rather than doing raw
    # asyncio socket I/O the way asyncpg did, so this may be unnecessary here
    # — kept as a safe default since it's unverified against a live loop
    # switch with this driver; NullPool makes every checkout a fresh
    # connection either way, at some perf cost only in tests.
    engine = create_async_engine(settings.database_url, poolclass=NullPool, **_engine_kwargs)
else:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, **_engine_kwargs)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
