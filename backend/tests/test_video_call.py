from starlette.testclient import TestClient

from app.main import app
from tests.test_chat_ws import _signup_and_complete_profile


def test_video_call_offer_answer_ice_and_hangup():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc1a@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc1b@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # A (the man) calls B — video calling is independent of the
                # Bumble first-message restriction, so this must succeed even
                # though A couldn't have sent a text message first.
                ws_a.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_b.receive_json()
                assert offer["type"] == "call_offer"
                assert offer["caller_id"] == a_id
                call_id = offer["call_id"]

                ws_b.send_json({"type": "call_answer", "call_id": call_id, "sdp": "fake-answer-sdp"})
                answer = ws_a.receive_json()
                assert answer == {"type": "call_answer", "call_id": call_id, "sdp": "fake-answer-sdp"}

                ws_a.send_json({"type": "call_ice_candidate", "call_id": call_id, "candidate": "cand-1"})
                ice = ws_b.receive_json()
                assert ice == {"type": "call_ice_candidate", "call_id": call_id, "candidate": "cand-1"}

                ws_b.send_json({"type": "call_end", "call_id": call_id, "reason": "hangup"})
                ended = ws_a.receive_json()
                assert ended == {"type": "call_end", "call_id": call_id, "reason": "hangup"}


def test_video_call_to_offline_peer_ends_immediately():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc2a@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc2b@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        # B is never connected via WS in this test.
        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            ws_a.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
            ended = ws_a.receive_json()
            assert ended["type"] == "call_end"
            assert ended["reason"] == "peer_offline"


def test_disconnect_mid_call_notifies_peer():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc3a@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc3b@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
            with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
                ws_a.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_b.receive_json()
                call_id = offer["call_id"]
                ws_b.send_json({"type": "call_answer", "call_id": call_id, "sdp": "fake-answer-sdp"})
                ws_a.receive_json()  # the call_answer forwarded to A

                # Explicitly signal the disconnect and read the notification
                # here, before this `with` block's own __exit__ runs. Letting
                # __exit__ trigger the disconnect instead is racy: right
                # after closing, it also cancels the server-side task
                # group (WebSocketTestSession._notify_close ->
                # cancel_scope.cancel()), which can interrupt the
                # ws_chat() finally block's `await manager.send_to_user(...)`
                # before the notification actually reaches B — this hung
                # ws_b.receive_json() forever until pytest-timeout caught it.
                # A real deployment doesn't have this race (uvicorn lets the
                # handler's own cleanup run to completion on disconnect).
                ws_a.close()
                ended = ws_b.receive_json()
                assert ended["type"] == "call_end"
                assert ended["reason"] == "peer_offline"
