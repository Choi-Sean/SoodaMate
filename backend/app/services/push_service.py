import uuid

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.device import PushToken
from app.models.user import User
from app.services import push_i18n

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


async def _get_language(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    return await db.scalar(select(User.preferred_language).where(User.id == user_id))


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
    lang = await _get_language(db, user_id)
    await send_to_user(
        db,
        user_id,
        push_i18n.t(lang, "match_title"),
        push_i18n.t(lang, "match_body"),
        {"type": "match", "match_id": str(match_id)},
    )


async def send_like_notification(db: AsyncSession, user_id: uuid.UUID, superlike: bool) -> None:
    # Deliberately doesn't name who liked them — that's the Likes tab's own
    # (free-tier-visible) reveal, this is just an awareness ping, same as
    # Tinder/Bumble's "someone liked you" push.
    lang = await _get_language(db, user_id)
    key_prefix = "superlike" if superlike else "like"
    await send_to_user(
        db,
        user_id,
        push_i18n.t(lang, f"{key_prefix}_title"),
        push_i18n.t(lang, f"{key_prefix}_body"),
        {"type": "like"},
    )


async def send_message_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    match_id: uuid.UUID,
    sender_id: uuid.UUID,
    sender_name: str,
    message_type: str = "text",
) -> None:
    lang = await _get_language(db, user_id)
    body_key = "photo_message_body" if message_type == "image" else "message_body"
    await send_to_user(
        db,
        user_id,
        sender_name,
        push_i18n.t(lang, body_key),
        {"type": "message", "match_id": str(match_id), "sender_id": str(sender_id)},
    )


async def send_couple_story_request_notification(
    db: AsyncSession, user_id: uuid.UUID, author_name: str, story_id: uuid.UUID
) -> None:
    lang = await _get_language(db, user_id)
    await send_to_user(
        db,
        user_id,
        author_name,
        push_i18n.t(lang, "couple_story_request_body"),
        {"type": "couple_story_request", "story_id": str(story_id)},
    )


async def send_couple_story_published_notification(db: AsyncSession, user_id: uuid.UUID, story_id: uuid.UUID) -> None:
    lang = await _get_language(db, user_id)
    await send_to_user(
        db,
        user_id,
        push_i18n.t(lang, "couple_story_published_title"),
        push_i18n.t(lang, "couple_story_published_body"),
        {"type": "couple_story_published", "story_id": str(story_id)},
    )


async def send_verification_result_notification(db: AsyncSession, user_id: uuid.UUID, approved: bool) -> None:
    lang = await _get_language(db, user_id)
    key_prefix = "verification_approved" if approved else "verification_rejected"
    await send_to_user(
        db,
        user_id,
        push_i18n.t(lang, f"{key_prefix}_title"),
        push_i18n.t(lang, f"{key_prefix}_body"),
        {"type": "verification", "status": "approved" if approved else "rejected"},
    )
