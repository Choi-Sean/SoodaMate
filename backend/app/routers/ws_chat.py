import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import rate_limit
from app.core.security import decode_token
from app.database import async_session_factory
from app.models.call import CallSession
from app.models.profile import Profile
from app.models.user import User
from app.services import call_service, chat_service, push_service, storage_service, translation_service
from app.services.match_service import mask_display_name
from app.ws.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# Everything a client can push over this socket is capped: unbounded frames and
# unbounded translation calls are both a cost/DoS lever.
MAX_MESSAGE_CHARS = 2000
MAX_SDP_CHARS = 20_000
MAX_CANDIDATE_CHARS = 2_000
MESSAGES_PER_10S = 30
FRAMES_PER_10S = 120
TRANSLATE_CHARS_PER_HOUR = 30_000
CALL_END_REASONS = {"hangup", "declined", "busy", "missed", "timeout", "peer_offline", "error"}
# How long an offer rings before it's treated as a missed call if nobody answers.
RING_TIMEOUT_SECONDS = 45


async def _authenticate(token: str, db: AsyncSession) -> User | None:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError, TypeError):
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.is_banned:
        return None
    return user


async def _error(user_id: uuid.UUID, code: str, **extra) -> None:
    await manager.send_to_user(user_id, {"type": "error", "code": code, **extra})


async def _handle_message(db: AsyncSession, user: User, data: dict) -> None:
    message_type = data.get("message_type") or "text"
    if message_type not in ("text", "image"):
        return
    content = data.get("content") if isinstance(data.get("content"), str) else ""
    content = content.strip()
    image_object_path = data.get("image_object_path") if message_type == "image" else None
    if message_type == "text" and not content:
        return
    try:
        match_id = uuid.UUID(data["match_id"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return

    if not rate_limit.allow("ws:msg", str(user.id), MESSAGES_PER_10S, 10):
        await _error(user.id, "rate_limited", match_id=str(match_id))
        return
    if len(content) > MAX_MESSAGE_CHARS:
        await _error(user.id, "message_too_long", match_id=str(match_id))
        return

    if message_type == "image":
        if (
            not isinstance(image_object_path, str)
            or image_object_path.endswith(".mp4")
            or not storage_service.is_valid_user_object_path(image_object_path, user.id, "chat")
        ):
            return
        problem = await asyncio.to_thread(storage_service.check_uploaded_object, image_object_path)
        if problem:
            await _error(user.id, "invalid_image", match_id=str(match_id))
            return

    match = await chat_service.get_active_match_for_user(db, match_id, user.id)
    if match is None:
        return

    if not chat_service.is_message_allowed(match, user.id):
        await _error(user.id, "first_message_restricted", match_id=str(match_id))
        return

    peer_id = chat_service.other_participant(match, user.id)

    # Real-time translation — text messages only, and only when configured
    # (translation_service.translate silently returns None otherwise) and
    # the two sides actually read the app in different languages. Computed
    # here (not in chat_service.persist_message) since it needs the peer's
    # preferred_language, which persist_message has no reason to know about.
    # Metered per user: translation is billed per character, so a user past
    # their hourly budget still chats, just without the translated copy.
    original_language: str | None = None
    translated_content: str | None = None
    translated_language: str | None = None
    if message_type == "text":
        peer_lang = await db.scalar(select(User.preferred_language).where(User.id == peer_id))
        sender_lang = user.preferred_language
        if (
            peer_lang
            and sender_lang
            and peer_lang != sender_lang
            and rate_limit.allow("ws:translate", str(user.id), TRANSLATE_CHARS_PER_HOUR, 3600, cost=len(content))
        ):
            translated = await translation_service.translate(content, target_lang=peer_lang, source_lang=sender_lang)
            if translated:
                original_language = sender_lang
                translated_content = translated
                translated_language = peer_lang

    message = await chat_service.persist_message(
        db,
        match,
        user.id,
        content,
        message_type=message_type,
        image_object_path=image_object_path,
        original_language=original_language,
        translated_content=translated_content,
        translated_language=translated_language,
    )

    payload = {
        "type": "message",
        "match_id": str(match_id),
        "message_id": str(message.id),
        "sender_id": str(user.id),
        "message_type": message_type,
        "content": content,
        "image_url": storage_service.build_public_url(image_object_path) if image_object_path else None,
        "original_language": original_language,
        "translated_content": translated_content,
        "translated_language": translated_language,
        "sent_at": message.sent_at.isoformat(),
    }
    delivered = await manager.send_to_user(peer_id, payload)
    if not delivered:
        sender_profile = await db.get(Profile, user.id)
        sender_name = sender_profile.display_name if sender_profile else "New message"
        # A blind chat stays anonymous until both sides agree to reveal: the
        # lock-screen notification must not carry the partner's real name.
        if match.is_blind and not match.blind_revealed:
            sender_name = mask_display_name(sender_name)
        await push_service.send_message_notification(
            db, peer_id, match_id, user.id, sender_name=sender_name, message_type=message_type
        )


async def _handle_read(db: AsyncSession, user: User, data: dict) -> None:
    try:
        match_id = uuid.UUID(data["match_id"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return

    match = await chat_service.get_active_match_for_user(db, match_id, user.id)
    if match is None:
        return

    await chat_service.mark_read(db, match_id, user.id)
    peer_id = chat_service.other_participant(match, user.id)
    await manager.send_to_user(peer_id, {"type": "read", "match_id": str(match_id)})


# --- Phase 15: video call signaling, piggybacked on this same connection ---
# (no second realtime channel). Gated by "match still active" — same check as
# messaging — and NOT tied to the Phase 14 first-message restriction; calling is
# independent of who's allowed to text first. Never inside an unrevealed blind
# chat: a call shows a face and exposes IP addresses through ICE candidates.


def _sdp_ok(sdp) -> bool:
    return isinstance(sdp, str) and 0 < len(sdp) <= MAX_SDP_CHARS


async def _ring_timeout(call_id: uuid.UUID, caller_id: uuid.UUID, callee_id: uuid.UUID, match_id: uuid.UUID) -> None:
    """Fired once per call_offer, RING_TIMEOUT_SECONDS later. Uses its own DB
    session (the request-scoped one from _handle_call_offer is long closed by
    then) and re-checks the call is still "ringing" before doing anything —
    a no-op if it was answered or ended in the meantime."""
    await asyncio.sleep(RING_TIMEOUT_SECONDS)
    try:
        async with async_session_factory() as db:
            call = await db.get(CallSession, call_id)
            if call is None or call.status != "ringing":
                return
            await call_service.mark_ended(db, call, "timeout")
            await manager.send_to_user(caller_id, {"type": "call_end", "call_id": str(call_id), "reason": "timeout"})
            await manager.send_to_user(callee_id, {"type": "call_end", "call_id": str(call_id), "reason": "timeout"})
            caller_profile = await db.get(Profile, caller_id)
            caller_name = caller_profile.display_name if caller_profile else "SooDaMate"
            await push_service.send_missed_call_notification(db, callee_id, match_id, caller_id, caller_name)
    except Exception:  # noqa: BLE001 - a background task's own bug must not go unnoticed, but must not crash anything either
        logger.exception("ring timeout handling failed for call %s", call_id)


async def _handle_call_offer(db: AsyncSession, user: User, data: dict) -> None:
    try:
        match_id = uuid.UUID(data["match_id"])
        sdp = data["sdp"]
    except (KeyError, ValueError, TypeError, AttributeError):
        return
    if not _sdp_ok(sdp):
        return

    match = await chat_service.get_active_match_for_user(db, match_id, user.id)
    if match is None:
        return
    if match.is_blind and not match.blind_revealed:
        await _error(user.id, "call_not_allowed", match_id=str(match_id))
        return
    # Bumble-style: in a man/woman match, only the woman may place the first
    # call — same restricted_to_user_id gate messaging already uses, so it
    # lifts the moment either side has sent a first message (reusing state
    # rather than adding a separate "first call" flag). Same-gender/'other'
    # pairs are unrestricted, per is_message_allowed.
    if not chat_service.is_message_allowed(match, user.id):
        await _error(user.id, "call_restricted", match_id=str(match_id))
        return
    if not rate_limit.allow("ws:call_offer", str(user.id), 5, 60):
        await _error(user.id, "rate_limited", match_id=str(match_id))
        return
    peer_id = chat_service.other_participant(match, user.id)

    call = await call_service.create_call(db, match_id, caller_id=user.id, callee_id=peer_id)
    caller_profile = await db.get(Profile, user.id)
    caller_name = caller_profile.display_name if caller_profile else "SooDaMate"

    if not manager.is_connected(peer_id):
        await call_service.mark_ended(db, call, "peer_offline")
        await manager.send_to_user(
            user.id, {"type": "call_end", "call_id": str(call.id), "reason": "peer_offline"}
        )
        # Not a ringing call (needs iOS VoIP push / PushKit, out of scope) — just
        # lets the callee know to open the app and call back. Calls are already
        # blocked entirely for an un-revealed blind match (checked above), so
        # there's no anonymity to protect in the caller's name here.
        await push_service.send_missed_call_notification(db, peer_id, match_id, user.id, caller_name)
        return

    # A normal push plays the OS's default sound/vibration once, which is what
    # actually gets a backgrounded phone's attention — not a continuously
    # ringing call screen (see send_incoming_call_notification's docstring).
    await push_service.send_incoming_call_notification(db, peer_id, match_id, user.id, caller_name)
    asyncio.create_task(_ring_timeout(call.id, caller_id=user.id, callee_id=peer_id, match_id=match_id))

    await manager.send_to_user(
        peer_id,
        {
            "type": "call_offer",
            "call_id": str(call.id),
            "match_id": str(match_id),
            "caller_id": str(user.id),
            "sdp": sdp,
        },
    )


async def _handle_call_answer(db: AsyncSession, user: User, data: dict) -> None:
    try:
        call_id = uuid.UUID(data["call_id"])
        sdp = data["sdp"]
    except (KeyError, ValueError, TypeError, AttributeError):
        return
    if not _sdp_ok(sdp):
        return

    call = await call_service.get_active_call_for_user(db, call_id, user.id)
    if call is None:
        return

    await call_service.mark_answered(db, call)
    caller_id = call_service.other_participant(call, user.id)
    await manager.send_to_user(caller_id, {"type": "call_answer", "call_id": str(call_id), "sdp": sdp})


async def _handle_call_ice_candidate(db: AsyncSession, user: User, data: dict) -> None:
    try:
        call_id = uuid.UUID(data["call_id"])
        candidate = data["candidate"]
        candidate_size = len(json.dumps(candidate))
    except (KeyError, ValueError, TypeError, AttributeError):
        return
    if candidate_size > MAX_CANDIDATE_CHARS:
        return

    call = await call_service.get_active_call_for_user(db, call_id, user.id)
    if call is None:
        return

    peer_id = call_service.other_participant(call, user.id)
    await manager.send_to_user(
        peer_id, {"type": "call_ice_candidate", "call_id": str(call_id), "candidate": candidate}
    )


async def _handle_call_end(db: AsyncSession, user: User, data: dict) -> None:
    try:
        call_id = uuid.UUID(data["call_id"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return
    # Stored in a 20-char column and echoed to the peer, so only known reasons.
    reason = data.get("reason")
    reason = reason if reason in CALL_END_REASONS else "hangup"

    call = await call_service.get_active_call_for_user(db, call_id, user.id)
    if call is None:
        return

    await call_service.mark_ended(db, call, reason)
    peer_id = call_service.other_participant(call, user.id)
    await manager.send_to_user(peer_id, {"type": "call_end", "call_id": str(call_id), "reason": reason})


_HANDLERS = {
    "message": _handle_message,
    "read": _handle_read,
    "call_offer": _handle_call_offer,
    "call_answer": _handle_call_answer,
    "call_ice_candidate": _handle_call_ice_candidate,
    "call_end": _handle_call_end,
}


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket, token: str = Query(...)) -> None:
    # No request-scoped DB session here on purpose: a session held for the life
    # of the socket keeps a pooled connection checked out while the user just
    # sits in a chat, and a few dozen idle chats would exhaust the pool and
    # stall the whole API. Each frame gets its own short-lived session instead.
    async with async_session_factory() as db:
        user = await _authenticate(token, db)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user.id
    await manager.connect(user_id, websocket)
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except (ValueError, KeyError, TypeError):
                continue  # not JSON / a binary frame — ignore, keep the socket
            if not isinstance(data, dict):
                continue
            handler = _HANDLERS.get(data.get("type")) if isinstance(data.get("type"), str) else None
            if handler is None:
                continue
            if not rate_limit.allow("ws:frame", str(user_id), FRAMES_PER_10S, 10):
                continue

            async with async_session_factory() as db:
                # Re-checked on every frame so banning/disabling an account
                # takes effect on sockets that are already open.
                current = await db.get(User, user_id)
                if current is None or not current.is_active or current.is_banned:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return
                try:
                    await handler(db, current, data)
                except Exception:  # noqa: BLE001 - one bad frame must not drop the connection
                    logger.exception("websocket handler %s failed", data.get("type"))
    except WebSocketDisconnect:
        pass
    finally:
        # A socket that was already replaced by a reconnect must not tear down
        # the user's calls or registration — those now belong to the new socket.
        was_current = manager.owns(user_id, websocket)
        manager.disconnect(user_id, websocket)
        # (No `return` in this finally block: it would swallow a cancellation or
        # an in-flight exception and hang task shutdown.)
        if was_current:
            try:
                async with async_session_factory() as db:
                    ended_calls = await call_service.end_active_calls_for_user(db, user_id, reason="peer_offline")
                    for call in ended_calls:
                        peer_id = call_service.other_participant(call, user_id)
                        await manager.send_to_user(
                            peer_id, {"type": "call_end", "call_id": str(call.id), "reason": "peer_offline"}
                        )
                        # This user was the callee of a call that was still ringing
                        # (never answered) when their connection dropped — a real
                        # missed call, not just a caller who cancelled or a call
                        # that had already connected and then dropped mid-conversation.
                        if call.callee_id == user_id and call.connected_at is None:
                            caller_profile = await db.get(Profile, call.caller_id)
                            caller_name = caller_profile.display_name if caller_profile else "SooDaMate"
                            await push_service.send_missed_call_notification(
                                db, user_id, call.match_id, call.caller_id, caller_name
                            )
            except Exception:  # noqa: BLE001
                logger.exception("websocket cleanup failed")
