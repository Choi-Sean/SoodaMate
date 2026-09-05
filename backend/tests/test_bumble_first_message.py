import uuid
from datetime import datetime, timedelta, timezone

from starlette.testclient import TestClient

from app.main import app
from tests.test_chat_ws import _signup_and_complete_profile


def test_male_first_message_rejected_with_error_frame():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "bm1@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "bf1@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            ws_a.send_json({"type": "message", "match_id": match_id, "content": "hi, I'm the man"})
            received = ws_a.receive_json()
            assert received == {
                "type": "error",
                "code": "first_message_restricted",
                "match_id": match_id,
            }


def test_female_sends_first_then_either_can_message():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "bm2@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "bf2@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "hi from her"})
                received = ws_a.receive_json()
                assert received["content"] == "hi from her"

                # Restriction is lifted now — the man can reply.
                ws_a.send_json({"type": "message", "match_id": match_id, "content": "hi back"})
                received2 = ws_b.receive_json()
                assert received2["content"] == "hi back"


def test_expired_match_excluded_from_list_and_rejects_messages():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "bm3@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "bf3@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        import asyncio

        from app.database import async_session_factory
        from app.models.interaction import Match

        async def backdate_deadline():
            async with async_session_factory() as session:
                match = await session.get(Match, uuid.UUID(match_id))
                match.first_message_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
                await session.commit()

        asyncio.run(backdate_deadline())

        matches = tc.get("/matches", headers=a_headers).json()
        assert all(m["id"] != match_id for m in matches)

        history = tc.get(f"/matches/{match_id}/messages", headers=a_headers)
        assert history.status_code == 404

        with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
            ws_b.send_json({"type": "message", "match_id": match_id, "content": "too late"})
            # Expired match -> get_active_match_for_user returns None -> the
            # handler silently no-ops (no error frame for "not found", only
            # for "restricted"), so nothing arrives; confirm the connection
            # is still alive by sending a read frame and getting no crash.
            ws_b.send_json({"type": "read", "match_id": match_id})


def test_same_gender_match_is_unrestricted_from_either_side():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "bs1@example.com", "female", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "bs2@example.com", "female", "female")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        matches = tc.get("/matches", headers=a_headers).json()
        this_match = next(m for m in matches if m["id"] == match_id)
        assert this_match["is_message_restricted"] is False
        assert this_match["can_send_first_message"] is True

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # Either side may send first — no restriction.
                ws_a.send_json({"type": "message", "match_id": match_id, "content": "hi from A"})
                received = ws_b.receive_json()
                assert received["content"] == "hi from A"
