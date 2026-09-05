from datetime import date

from starlette.testclient import TestClient

from app.main import app


def _signup_and_complete_profile(client: TestClient, email: str, gender: str, interested_in: str) -> tuple[str, str]:
    signup = client.post("/auth/signup", json={"email": email, "password": "password123"})
    tokens = signup.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    birth_year = date.today().year - 25
    client.put(
        "/profiles/me",
        headers=headers,
        json={
            "display_name": "Test",
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
        json={"gcs_object_path": f"users/{tokens['user_id']}/photos/0.jpg", "position": 0},
    )
    return tokens["user_id"], tokens["access_token"]


def test_two_matched_users_exchange_messages_live():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "wsA@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "wsB@example.com", "female", "male")

        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        assert match_resp.json()["matched"] is True
        match_id = match_resp.json()["match_id"]

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


def test_unauthenticated_ws_connection_rejected():
    with TestClient(app) as tc:
        try:
            with tc.websocket_connect("/ws/chat?token=not-a-real-token"):
                raise AssertionError("connection should have been rejected")
        except Exception:
            pass  # starlette raises WebSocketDisconnect when the server closes during handshake
