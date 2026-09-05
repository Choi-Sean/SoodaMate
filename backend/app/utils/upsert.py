from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def try_insert(db: AsyncSession, obj) -> bool:
    """Attempts to insert obj inside a SAVEPOINT. Returns True if it
    committed, False if it violated a unique/PK constraint — the portable
    replacement for Postgres-only ON CONFLICT, since MSSQL has no such clause
    short of a full MERGE statement. Caller decides what False means: update
    the existing row, treat as a no-op, or look up the existing id."""
    try:
        async with db.begin_nested():
            db.add(obj)
            await db.flush()
        return True
    except IntegrityError:
        return False
