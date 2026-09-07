from datetime import datetime, timezone


def is_premium(premium_until: datetime | None) -> bool:
    """Single source of truth for "is this premium_until value still
    active" — used both by ProfileOut.is_premium_member (the schema's
    computed field) and by service code that needs the same check on a
    raw ORM row (match_service's unlimited-swipes gate, etc)."""
    if premium_until is None:
        return False
    if premium_until.tzinfo is None:
        premium_until = premium_until.replace(tzinfo=timezone.utc)
    return premium_until > datetime.now(timezone.utc)
