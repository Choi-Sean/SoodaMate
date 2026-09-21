"""Retry helper for SQL Server deadlocks.

Two requests that touch the same tables in a different order (e.g. a block and a
swipe between the same two people) can deadlock; SQL Server resolves it by killing
one of them with error 1205 and documents "rerun the transaction" as the fix. The
caller passes a coroutine function that redoes the WHOLE unit of work, because a
rollback also discards everything done earlier in the same transaction.
"""
import asyncio

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession


def is_deadlock(exc: DBAPIError) -> bool:
    text = str(getattr(exc, "orig", exc))
    return "40001" in text or "(1205)" in text or "deadlock" in text.lower()


async def run_with_deadlock_retry(db: AsyncSession, unit_of_work, attempts: int = 3):
    for attempt in range(attempts):
        try:
            return await unit_of_work()
        except DBAPIError as exc:
            if not is_deadlock(exc) or attempt == attempts - 1:
                raise
            await db.rollback()
            await asyncio.sleep(0.05 * (attempt + 1))
