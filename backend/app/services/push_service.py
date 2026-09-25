import asyncio
import json
import logging
import uuid

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.device import PushToken
from app.models.user import User
from app.services import push_i18n

logger = logging.getLogger(__name__)

_app: firebase_admin.App | None = None
_init_attempted = False


def _get_app() -> firebase_admin.App | None:
    """Lazily initializes Firebase. Returns None (no-op mode) until the user
    has a real Firebase project and either FIREBASE_CREDENTIALS_JSON (the key
    file's content) or FIREBASE_CREDENTIALS_PATH is set — an external
    prerequisite, so push is best-effort/no-op until then rather than fatal.
    Every reason for staying off is logged once: a silently disabled push is
    exactly how the promo notifications went unnoticed."""
    global _app, _init_attempted
    if _init_attempted:
        return _app
    _init_attempted = True
    try:
        if settings.firebase_credentials_json:
            # strict=False tolerates raw newlines inside the private key when the
            # value was pasted without JSON escaping.
            cred = credentials.Certificate(json.loads(settings.firebase_credentials_json, strict=False))
        elif settings.firebase_credentials_path:
            cred = credentials.Certificate(settings.firebase_credentials_path)
        else:
            logger.warning("push notifications are OFF: neither FIREBASE_CREDENTIALS_JSON nor FIREBASE_CREDENTIALS_PATH is set")
            return None
        _app = firebase_admin.initialize_app(cred)
        logger.info("push notifications are ON (Firebase project %s)", getattr(_app, "project_id", "?"))
    except Exception as exc:  # noqa: BLE001 - never fatal; only the error type is logged, never key material
        logger.error("push notifications are OFF: Firebase credentials could not be loaded (%s)", type(exc).__name__)
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

    if not tokens:
        logger.info("push to user %s skipped: no registered device token", user_id)
        return

    for token in tokens:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=token,
            # Without an explicit sound iOS delivers the banner silently; high priority
            # so Android doesn't batch a match alert behind Doze.
            apns=messaging.APNSConfig(payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))),
            android=messaging.AndroidConfig(priority="high"),
        )
        try:
            # firebase_admin's send() is a blocking HTTP call: run it off the event
            # loop so a push (or a promo broadcast loop) never stalls chat sockets.
            await asyncio.to_thread(messaging.send, message, app=app)
        except Exception as exc:  # noqa: BLE001 - expired/invalid token etc.: best-effort, not fatal
            logger.warning("push to user %s failed (%s)", user_id, type(exc).__name__)


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


async def send_incoming_call_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    match_id: uuid.UUID,
    caller_id: uuid.UUID,
    caller_name: str,
    call_type: str = "video",
) -> None:
    """Sent alongside the live call_offer WS frame (routers/ws_chat.py::
    _handle_call_offer) when the callee IS connected — a normal push still plays
    the OS's default sound/vibration once on arrival, which is what actually
    gets a backgrounded phone's attention; it is NOT a continuously ringing
    call screen (that needs iOS PushKit/CallKit + an Android foreground
    service — real, separately-scoped native work, not built here). The
    in-app incoming-call screen is what "rings" for as long as the app is
    open."""
    lang = await _get_language(db, user_id)
    body_key = "incoming_call_body_audio" if call_type == "audio" else "incoming_call_body"
    await send_to_user(
        db,
        user_id,
        caller_name,
        push_i18n.t(lang, body_key),
        {"type": "incoming_call", "match_id": str(match_id), "caller_id": str(caller_id), "call_type": call_type},
    )


async def send_missed_call_notification(
    db: AsyncSession, user_id: uuid.UUID, match_id: uuid.UUID, caller_id: uuid.UUID, caller_name: str
) -> None:
    """Sent when a call never gets answered: the callee was never connected, the
    45s ring timed out, or the callee's connection dropped while it was still
    ringing (routers/ws_chat.py). Always goes to the callee — the one who,
    from the app's perspective, "missed" the call."""
    lang = await _get_language(db, user_id)
    await send_to_user(
        db,
        user_id,
        caller_name,
        push_i18n.t(lang, "missed_call_body"),
        {"type": "missed_call", "match_id": str(match_id), "caller_id": str(caller_id)},
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
    body_key = (
        "photo_message_body"
        if message_type == "image"
        else "voice_message_body" if message_type == "voice" else "message_body"
    )
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


async def send_blind_chat_matched_notification(db: AsyncSession, user_id: uuid.UUID, match_id: uuid.UUID) -> None:
    lang = await _get_language(db, user_id)
    await send_to_user(
        db,
        user_id,
        push_i18n.t(lang, "blind_matched_title"),
        push_i18n.t(lang, "blind_matched_body"),
        {"type": "blind_chat_matched", "match_id": str(match_id)},
    )


async def send_blind_reveal_requested_notification(db: AsyncSession, user_id: uuid.UUID, match_id: uuid.UUID) -> None:
    lang = await _get_language(db, user_id)
    await send_to_user(
        db,
        user_id,
        push_i18n.t(lang, "blind_reveal_requested_title"),
        push_i18n.t(lang, "blind_reveal_requested_body"),
        {"type": "blind_reveal_requested", "match_id": str(match_id)},
    )


async def send_blind_reveal_accepted_notification(db: AsyncSession, user_id: uuid.UUID, match_id: uuid.UUID) -> None:
    lang = await _get_language(db, user_id)
    await send_to_user(
        db,
        user_id,
        push_i18n.t(lang, "blind_reveal_accepted_title"),
        push_i18n.t(lang, "blind_reveal_accepted_body"),
        {"type": "blind_reveal_accepted", "match_id": str(match_id)},
    )


async def send_promo_broadcast_notification(db: AsyncSession, product_id: str, discount_percent: int) -> None:
    """Sent to every device with a registered token when an admin activates
    a Promotion (routers/admin.py) — not scoped to a single user like every
    other send_*_notification above, since a discount is store-wide. Loops
    per-user (not a single FCM multicast) so each person still gets the
    title/body AND the product name itself in their own preferred_language
    (push_i18n covers all five app languages; an unknown language falls
    back to English, same as every other push)."""
    from app.services.payment_service import PRODUCTS, _localized_product_name

    product = PRODUCTS.get(product_id)
    if product is None:
        return

    user_ids = (await db.execute(select(PushToken.user_id).distinct())).scalars().all()
    for user_id in user_ids:
        lang = await _get_language(db, user_id)
        product_name = _localized_product_name(product_id, product, lang if lang in push_i18n.SUPPORTED_PUSH_LANGUAGES else "en")
        await send_to_user(
            db,
            user_id,
            push_i18n.t(lang, "promo_title", product=product_name, discount=discount_percent),
            push_i18n.t(lang, "promo_body"),
            {"type": "promo", "product_id": product_id, "discount_percent": discount_percent},
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
