import uuid

from fastapi import WebSocket


class ConnectionManager:
    """One active WebSocket per user (v1: single device). Delivery is
    best-effort — callers fall back to push notifications when send_to_user
    returns False."""

    def __init__(self) -> None:
        self._connections: dict[uuid.UUID, WebSocket] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[user_id] = websocket

    def disconnect(self, user_id: uuid.UUID) -> None:
        self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: uuid.UUID, payload: dict) -> bool:
        websocket = self._connections.get(user_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            self._connections.pop(user_id, None)
            return False

    def is_connected(self, user_id: uuid.UUID) -> bool:
        return user_id in self._connections


manager = ConnectionManager()
