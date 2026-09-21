"""Per-key asyncio locks for read-then-write sequences that must not interleave
for the same user (swipe-limit check + insert, credit spend, queue join).

Without them, N parallel requests from one account all read "remaining > 0"
before any of them writes, so a script can blow straight through a daily limit
or spend one paid credit several times. The API runs as a single process (see
rate_limit.py), so an in-process lock is exact; scaling out would need a
database-level guard instead (e.g. an UPDATE ... WHERE credits > 0).

Locks live in a WeakValueDictionary, so an idle key costs nothing: the entry
vanishes as soon as nobody is holding or waiting on it.
"""
import asyncio
import weakref

_locks: "weakref.WeakValueDictionary[str, asyncio.Lock]" = weakref.WeakValueDictionary()


def user_lock(key: str) -> asyncio.Lock:
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock
