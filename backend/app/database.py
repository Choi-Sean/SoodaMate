from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# deprecate_large_types: MSSQL-only engine option so Text/UnicodeText columns
# compile to modern NVARCHAR(MAX) instead of the legacy NTEXT type.
_engine_kwargs = {"deprecate_large_types": True}

if settings.app_env == "test":
    # Confirmed (not just theorized) empirically: switching this to a normal
    # pooled engine to chase down an intermittent
    # `Windows fatal exception: access violation` crash made things *worse*
    # — aioodbc connections reused across pytest-asyncio's per-function event
    # loop / TestClient's background-thread portal loop failed with
    # "RuntimeError: ... attached to a different loop" (aioodbc wraps pyodbc
    # calls in a thread executor, but the Future/Task bookkeeping around that
    # is still loop-bound). NullPool avoids that by never reusing a
    # connection across checkouts. The rarer access-violation crash (pyodbc
    # connection teardown racing Python's GC finalizer on another thread,
    # roughly 1-in-4 full runs) is real but strictly less disruptive than the
    # cross-loop failure mode a real pool introduces here — pytest-timeout
    # bounds the damage either way. Re-evaluate if aioodbc/pyodbc ships a fix
    # for either failure mode.
    engine = create_async_engine(settings.database_url, poolclass=NullPool, **_engine_kwargs)
else:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, **_engine_kwargs)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

# func.now() compiles to MSSQL's CURRENT_TIMESTAMP (== GETDATE()), which
# returns the DB SERVER's OS-local time, not UTC — confirmed empirically on
# this server (several hours behind UTC). Every server_default=func.now()
# timestamp column was silently skewed against the UTC "today" boundaries
# services compute in Python (e.g. blind_chat_service's daily free-match
# limit undercounting matches made in the first few UTC hours of each day).
# Same cross-dialect trap, and same fix pattern, as discovery_service's
# _ORDER_RANDOM (func.newid() vs func.random()) — resolved once at import
# time from the dialect actually in use.
#
# server_default alone can't fix rows on the *existing* live table, though:
# it's a DDL-time construct (only takes effect for a fresh CREATE/ALTER),
# and this DB's columns already carry the old GETDATE()-based constraint
# from whenever each table was first created. Every model below also sets
# default=utc_now — a client-side Python default, computed and sent by the
# ORM with every INSERT (the same mechanism every model already relies on
# for id=uuid.uuid4) — which is what actually corrects the live behavior,
# no migration required, since it wins over server_default whenever the ORM
# is doing the inserting (i.e. always, in this codebase).
utc_now_default = func.getutcdate() if engine.dialect.name == "mssql" else func.now()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
