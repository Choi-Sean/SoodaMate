"""Small in-process sliding-window rate limiter.

The API runs as a single Railway instance, so per-process counters are exact;
if it is ever scaled out, swap the storage here for Redis without touching the
call sites (they only use enforce()/allow()/the limit_* dependencies).

Design notes
- Keys are scoped by a name plus what is being protected. The abuse that costs
  money or breaks accounts is keyed by the TARGET (phone number, email, user
  id) rather than by IP, because carriers in Korea put many real users behind
  one shared IP and an attacker can rotate IPs freely. IP limits exist as a
  second, generous layer.
- Requests are refused with HTTP 429 + Retry-After; the mobile app maps that
  to a friendly localized message.
"""
import threading
import time
from collections import deque

from fastapi import Depends, HTTPException, Request, status

from app.config import settings

_lock = threading.Lock()
# key -> (window_seconds, deque[(timestamp, cost)])
_events: dict[str, tuple[int, deque]] = {}
_last_sweep = 0.0

TOO_MANY = "too many requests, please try again later"


def reset() -> None:
    with _lock:
        _events.clear()


def client_ip(request) -> str:
    """The caller's IP as seen by the platform's edge proxy: the Nth-from-last
    X-Forwarded-For entry (settings.trusted_proxy_hops; the one the trusted proxy
    appended — entries further left are client-controlled and spoofable)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            hops = max(1, settings.trusted_proxy_hops)
            return parts[-hops] if len(parts) >= hops else parts[0]
    client = request.client
    return client.host if client else "unknown"


def _sweep(now: float) -> None:
    global _last_sweep
    if now - _last_sweep < 60:
        return
    _last_sweep = now
    stale = [k for k, (window, q) in _events.items() if not q or q[-1][0] < now - window]
    for k in stale:
        del _events[k]


def _hit(key: str, limit: int, window: int, cost: int) -> int | None:
    """Records the event and returns None, or returns the seconds to wait if
    it would exceed `limit` within the trailing `window` seconds."""
    now = time.monotonic()
    with _lock:
        _sweep(now)
        entry = _events.get(key)
        if entry is None:
            entry = (window, deque())
            _events[key] = entry
        q = entry[1]
        cutoff = now - window
        while q and q[0][0] <= cutoff:
            q.popleft()
        used = sum(c for _, c in q)
        if used + cost > limit:
            oldest = q[0][0] if q else now
            return max(1, int(oldest + window - now) + 1)
        q.append((now, cost))
        return None


def allow(scope: str, key: str, limit: int, window: int, cost: int = 1) -> bool:
    """Non-raising variant (WebSocket frames, budget checks)."""
    if not settings.rate_limit_enabled:
        return True
    return _hit(f"{scope}:{key}", limit, window, cost) is None


def enforce(scope: str, key: str, limit: int, window: int, cost: int = 1) -> None:
    if not settings.rate_limit_enabled:
        return
    retry_after = _hit(f"{scope}:{key}", limit, window, cost)
    if retry_after is not None:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, TOO_MANY, headers={"Retry-After": str(retry_after)}
        )


def limit_ip(scope: str, limit: int, window: int):
    """Route dependency: at most `limit` calls per `window` seconds per client IP."""

    async def dependency(request: Request) -> None:
        enforce(f"ip:{scope}", client_ip(request), limit, window)

    return dependency


def limit_user(scope: str, limit: int, window: int):
    """Route dependency: at most `limit` calls per `window` seconds per logged-in user."""
    from app.deps import get_current_user  # local import: deps must not depend on this module

    async def dependency(user=Depends(get_current_user)) -> None:
        enforce(f"user:{scope}", str(user.id), limit, window)

    return dependency
