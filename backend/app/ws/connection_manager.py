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
        previous = self._connections.get(user_id)
        self._connections[user_id] = websocket
        if previous is not None and previous is not websocket:
            # A reconnect (flaky mobile network, app relaunch) leaves the old
            # socket half-open on the server for a while; close it so it can't
            # linger as a second live connection for the same account.
            try:
                await previous.close()
            except Exception:  # noqa: BLE001 - already dead
                pass

    def disconnect(self, user_id: uuid.UUID, websocket: WebSocket | None = None) -> None:
        """Only removes the entry if it still belongs to `websocket` — otherwise
        a stale socket finishing AFTER the user reconnected would unregister the
        new, healthy connection and silently drop them to push-only delivery."""
        if websocket is not None and self._connections.get(user_id) is not websocket:
            return
        self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: uuid.UUID, payload: dict) -> bool:
        websocket = self._connections.get(user_id)
        if websocket is None:
            return False
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            if self._connections.get(user_id) is websocket:
                self._connections.pop(user_id, None)
            return False

    def owns(self, user_id: uuid.UUID, websocket: WebSocket) -> bool:
        """True while `websocket` is still the user's registered connection."""
        return self._connections.get(user_id) is websocket

    def is_connected(self, user_id: uuid.UUID) -> bool:
        return user_id in self._connections


manager = ConnectionManager()
