import uuid

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.device import PushToken

_app: firebase_admin.App | None = None
_init_attempted = False


def _get_app() -> firebase_admin.App | None:
    """Lazily initializes Firebase. Returns None (no-op mode) until the user
    has a real Firebase project and FIREBASE_CREDENTIALS_PATH is set — this
    is an external prerequisite the user creates, not something Claude can
    provision, so push is best-effort/no-op until then rather than fatal."""
    global _app, _init_attempted
    if _init_attempted:
        return _app
    _init_attempted = True
    if not settings.firebase_credentials_path:
        return None
    try:
        cred = credentials.Certificate(settings.firebase_credentials_path)
        _app = firebase_admin.initialize_app(cred)
    except Exception:
        _app = None
    return _app


async def send_to_user(
    db: AsyncSession, user_id: uuid.UUID, title: str, body: str, data: dict | None = None
) -> None:
    app = _get_app()
    if app is None:
        return

    tokens = (
        await db.execute(select(PushToken.fcm_token).where(PushToken.user_id == user_id))
    ).scalars().all()

    for token in tokens:
        try:
            messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={k: str(v) for k, v in (data or {}).items()},
                    token=token,
                ),
                app=app,
            )
        except Exception:
            pass  # expired/invalid token etc. — best-effort, not fatal


async def send_match_notification(db: AsyncSession, user_id: uuid.UUID, match_id: uuid.UUID) -> None:
    await send_to_user(
        db,
        user_id,
        "It's a match!",
        "You have a new match on SuDa Mate",
        {"type": "match", "match_id": str(match_id)},
    )


async def send_message_notification(
    db: AsyncSession, user_id: uuid.UUID, match_id: uuid.UUID, sender_id: uuid.UUID, sender_name: str
) -> None:
    await send_to_user(
        db,
        user_id,
        sender_name,
        "sent you a message",
        {"type": "message", "match_id": str(match_id), "sender_id": str(sender_id)},
    )
