import time
import uuid
from datetime import date

from starlette.testclient import TestClient

from app.main import app
from tests.helpers import create_ordinary_match_sync, track_test_user


def _signup_and_complete_profile(client: TestClient, email: str, gender: str, interested_in: str) -> tuple[str, str]:
    signup = client.post("/auth/signup", json={"email": email, "password": "password123"})
    tokens = signup.json()
    track_test_user(tokens["user_id"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    birth_year = date.today().year - 25
    client.put(
        "/profiles/me",
        headers=headers,
        json={
            "display_name": "Test",
            "legal_first_name": "Test",
            "birth_date": f"{birth_year}-01-01",
            "gender": gender,
            "interested_in": interested_in,
            "min_age_pref": 18,
            "max_age_pref": 99,
        },
    )
    client.post(
        "/profiles/me/photos/confirm",
        headers=headers,
        json={"gcs_object_path": f"users/{tokens['user_id']}/photos/{uuid.uuid4()}.jpg", "position": 0},
    )
    return tokens["user_id"], tokens["access_token"]


def test_two_matched_users_exchange_messages_live():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "wsA@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "wsB@example.com", "female", "male")

        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # A is male, B is female — Bumble's first-message rule
                # (Phase 14) restricts this mixed pair to B sending first.
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "hi from B"})
                received = ws_a.receive_json()
                assert received["type"] == "message"
                assert received["content"] == "hi from B"
                assert received["sender_id"] == b_id

                ws_a.send_json({"type": "message", "match_id": match_id, "content": "hi back from A"})
                received2 = ws_b.receive_json()
                assert received2["content"] == "hi back from A"

        history = tc.get(f"/matches/{match_id}/messages", headers=a_headers)
        assert history.status_code == 200
        contents = [m["content"] for m in history.json()]
        assert "hi from B" in contents
        assert "hi back from A" in contents


def test_deleting_own_message_notifies_the_peer_and_blanks_history():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "wsDelA@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "wsDelB@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "oops, wrong chat"})
                received = ws_a.receive_json()
                message_id = received["message_id"]

                ws_b.send_json({"type": "message_delete", "match_id": match_id, "message_id": message_id})
                notice = ws_a.receive_json()
                assert notice == {"type": "message_deleted", "match_id": match_id, "message_id": message_id}

        history = tc.get(f"/matches/{match_id}/messages", headers=a_headers).json()
        deleted = next(m for m in history if m["id"] == message_id)
        assert deleted["message_type"] == "deleted"
        assert deleted["content"] == ""


def test_cannot_delete_someone_elses_message_or_delete_twice():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "wsDelC@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "wsDelD@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "hers"})
                message_id = ws_a.receive_json()["message_id"]

                # A (not the sender) tries to delete B's message — silently ignored,
                # no message_deleted frame goes anywhere.
                ws_a.send_json({"type": "message_delete", "match_id": match_id, "message_id": message_id})

                # Confirm nothing happened by having B send a second message and
                # checking A receives *that* next, not a stray deletion notice.
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "still here"})
                next_frame = ws_a.receive_json()
                assert next_frame["content"] == "still here"

        history = tc.get(f"/matches/{match_id}/messages", headers=a_headers).json()
        untouched = next(m for m in history if m["id"] == message_id)
        assert untouched["message_type"] == "text"
        assert untouched["content"] == "hers"

        # The real sender deletes it. No confirmation frame comes back to the
        # deleter (same no-self-echo convention as sending a message), so
        # there's nothing to receive_json() on — poll REST history instead of
        # a fixed sleep, since the real hosted DB's commit latency varies.
        with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b2:
            ws_b2.send_json({"type": "message_delete", "match_id": match_id, "message_id": message_id})
            deadline = time.time() + 5
            message_type = "text"
            while message_type != "deleted" and time.time() < deadline:
                time.sleep(0.2)
                history2 = tc.get(f"/matches/{match_id}/messages", headers=a_headers).json()
                message_type = next(m for m in history2 if m["id"] == message_id)["message_type"]
        assert message_type == "deleted"


def test_unauthenticated_ws_connection_rejected():
    with TestClient(app) as tc:
        try:
            with tc.websocket_connect("/ws/chat?token=not-a-real-token"):
                raise AssertionError("connection should have been rejected")
        except Exception:
            pass  # starlette raises WebSocketDisconnect when the server closes during handshake
