import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db
from app.models.profile import Profile
from app.models.user import User
from app.services import call_service, chat_service, push_service
from app.ws.connection_manager import manager

router = APIRouter(tags=["chat"])


async def _authenticate(token: str, db: AsyncSession) -> User | None:
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active or user.is_banned:
        return None
    return user


async def _handle_message(db: AsyncSession, user: User, data: dict) -> None:
    content = (data.get("content") or "").strip()
    if not content:
        return
    try:
        match_id = uuid.UUID(data["match_id"])
    except (KeyError, ValueError, TypeError):
        return

    match = await chat_service.get_active_match_for_user(db, match_id, user.id)
    if match is None:
        return

    if not chat_service.is_message_allowed(match, user.id):
        await manager.send_to_user(
            user.id,
            {"type": "error", "code": "first_message_restricted", "match_id": str(match_id)},
        )
        return

    message = await chat_service.persist_message(db, match, user.id, content)
    peer_id = chat_service.other_participant(match, user.id)

    payload = {
        "type": "message",
        "match_id": str(match_id),
        "message_id": str(message.id),
        "sender_id": str(user.id),
        "content": content,
        "sent_at": message.sent_at.isoformat(),
    }
    delivered = await manager.send_to_user(peer_id, payload)
    if not delivered:
        sender_profile = await db.get(Profile, user.id)
        sender_name = sender_profile.display_name if sender_profile else "New message"
        await push_service.send_message_notification(db, peer_id, match_id, user.id, sender_name=sender_name)


async def _handle_read(db: AsyncSession, user: User, data: dict) -> None:
    try:
        match_id = uuid.UUID(data["match_id"])
    except (KeyError, ValueError, TypeError):
        return

    match = await chat_service.get_active_match_for_user(db, match_id, user.id)
    if match is None:
        return

    await chat_service.mark_read(db, match_id, user.id)
    peer_id = chat_service.other_participant(match, user.id)
    await manager.send_to_user(peer_id, {"type": "read", "match_id": str(match_id)})


# --- Phase 15: video call signaling, piggybacked on this same connection ---
# (no second realtime channel). Gated only by "match still active" — same
# check as messaging — deliberately NOT tied to the Phase 14 first-message
# restriction; calling is independent of who's allowed to text first.


async def _handle_call_offer(db: AsyncSession, user: User, data: dict) -> None:
    try:
        match_id = uuid.UUID(data["match_id"])
        sdp = data["sdp"]
    except (KeyError, ValueError, TypeError):
        return

    match = await chat_service.get_active_match_for_user(db, match_id, user.id)
    if match is None:
        return
    peer_id = chat_service.other_participant(match, user.id)

    call = await call_service.create_call(db, match_id, caller_id=user.id, callee_id=peer_id)

    if not manager.is_connected(peer_id):
        await call_service.mark_ended(db, call, "peer_offline")
        await manager.send_to_user(
            user.id, {"type": "call_end", "call_id": str(call.id), "reason": "peer_offline"}
        )
        return

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
    except (KeyError, ValueError, TypeError):
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
    except (KeyError, ValueError, TypeError):
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
    except (KeyError, ValueError, TypeError):
        return
    reason = data.get("reason", "hangup")

    call = await call_service.get_active_call_for_user(db, call_id, user.id)
    if call is None:
        return

    await call_service.mark_ended(db, call, reason)
    peer_id = call_service.other_participant(call, user.id)
    await manager.send_to_user(peer_id, {"type": "call_end", "call_id": str(call_id), "reason": reason})


@router.websocket("/ws/chat")
async def ws_chat(
    websocket: WebSocket, token: str = Query(...), db: AsyncSession = Depends(get_db)
) -> None:
    user = await _authenticate(token, db)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(user.id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            if msg_type == "message":
                await _handle_message(db, user, data)
            elif msg_type == "read":
                await _handle_read(db, user, data)
            elif msg_type == "call_offer":
                await _handle_call_offer(db, user, data)
            elif msg_type == "call_answer":
                await _handle_call_answer(db, user, data)
            elif msg_type == "call_ice_candidate":
                await _handle_call_ice_candidate(db, user, data)
            elif msg_type == "call_end":
                await _handle_call_end(db, user, data)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user.id)
        ended_calls = await call_service.end_active_calls_for_user(db, user.id, reason="peer_offline")
        for call in ended_calls:
            peer_id = call_service.other_participant(call, user.id)
            await manager.send_to_user(
                peer_id, {"type": "call_end", "call_id": str(call.id), "reason": "peer_offline"}
            )
