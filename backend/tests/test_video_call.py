import time

import pytest
from starlette.testclient import TestClient

from app.main import app
from tests.helpers import create_ordinary_match_sync
from tests.test_chat_ws import _signup_and_complete_profile


async def _noop(*args, **kwargs):
    return None


def test_video_call_offer_answer_ice_and_hangup():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc1a@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc1b@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # B (the woman) calls A — the only side allowed to place the
                # first call in a man/woman match, same rule as the first text
                # message (see test_video_call_only_the_woman_may_call_first).
                ws_b.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_a.receive_json()
                assert offer["type"] == "call_offer"
                assert offer["caller_id"] == b_id
                call_id = offer["call_id"]

                ws_a.send_json({"type": "call_answer", "call_id": call_id, "sdp": "fake-answer-sdp"})
                answer = ws_b.receive_json()
                assert answer == {"type": "call_answer", "call_id": call_id, "sdp": "fake-answer-sdp"}

                ws_b.send_json({"type": "call_ice_candidate", "call_id": call_id, "candidate": "cand-1"})
                ice = ws_a.receive_json()
                assert ice == {"type": "call_ice_candidate", "call_id": call_id, "candidate": "cand-1"}

                ws_a.send_json({"type": "call_end", "call_id": call_id, "reason": "hangup"})
                ended = ws_b.receive_json()
                assert ended == {"type": "call_end", "call_id": call_id, "reason": "hangup"}


def test_video_call_only_the_woman_may_call_first_then_it_opens_up_for_both():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc0a@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc0b@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # A (the man) tries to call first — blocked, same as the first
                # message rule, and B never sees an offer.
                ws_a.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                blocked = ws_a.receive_json()
                assert blocked == {"type": "error", "code": "call_restricted", "match_id": match_id}

                # Once B has sent the first text message, the restriction lifts
                # for calling too (it reuses the same match.first_message_sent
                # state, not a separate "first call" flag).
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "hi"})
                ws_a.receive_json()  # the text message itself

                ws_a.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp-2"})
                offer = ws_b.receive_json()
                assert offer["type"] == "call_offer"
                assert offer["caller_id"] == a_id


def test_video_call_same_gender_pair_is_unrestricted():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc0c@example.com", "male", "male")
        b_id, b_token = _signup_and_complete_profile(tc, "vc0d@example.com", "male", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_a.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_b.receive_json()
                assert offer["type"] == "call_offer"


def test_video_call_to_offline_peer_ends_immediately_and_sends_a_missed_call_push(monkeypatch):
    import app.routers.ws_chat as ws_chat

    sent = []

    async def fake_send_missed_call_notification(db, user_id, match_id, caller_id, caller_name):
        sent.append((user_id, match_id, caller_id, caller_name))

    monkeypatch.setattr(ws_chat.push_service, "send_missed_call_notification", fake_send_missed_call_notification)

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc2a@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc2b@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        # A is never connected via WS in this test. B (the woman) calls him.
        with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
            ws_b.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
            ended = ws_b.receive_json()
            assert ended["type"] == "call_end"
            assert ended["reason"] == "peer_offline"

            # The call_end frame to the caller is sent one await *before* the push
            # to the callee (see routers/ws_chat.py::_handle_call_offer) — receiving
            # it over the wire doesn't guarantee the server-side coroutine handling
            # this frame has reached that later line yet. Crucially, must poll
            # *inside* this `with` block: closing the socket cancels the in-flight
            # server task still processing this same frame, cutting it off mid-await.
            deadline = time.time() + 5
            while not sent and time.time() < deadline:
                time.sleep(0.1)
        assert len(sent) == 1
        user_id, sent_match_id, caller_id, caller_name = sent[0]
        assert str(user_id) == a_id  # the offline callee, not the caller
        assert str(sent_match_id) == match_id
        assert str(caller_id) == b_id
        assert caller_name == "Test"  # _signup_and_complete_profile's default display_name


def test_video_call_offer_to_a_connected_peer_sends_an_incoming_call_push_not_a_missed_one(monkeypatch):
    import app.routers.ws_chat as ws_chat

    incoming = []
    monkeypatch.setattr(
        ws_chat.push_service,
        "send_missed_call_notification",
        lambda *a, **k: pytest.fail("must not be called for a connected callee that hasn't timed out"),
    )

    async def fake_send_incoming_call_notification(db, user_id, match_id, caller_id, caller_name, call_type="video"):
        incoming.append((user_id, match_id, caller_id, caller_name, call_type))

    monkeypatch.setattr(ws_chat.push_service, "send_incoming_call_notification", fake_send_incoming_call_notification)
    # No live ring for this test — avoid a background timeout task outliving it.
    monkeypatch.setattr(ws_chat, "RING_TIMEOUT_SECONDS", 3600)

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc2c@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc2d@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # No call_type sent — defaults to "video" (backward compat with
                # any client that predates audio calling).
                ws_b.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_a.receive_json()
                assert offer["type"] == "call_offer"
                assert offer["call_type"] == "video"

                deadline = time.time() + 5
                while not incoming and time.time() < deadline:
                    time.sleep(0.1)
        assert len(incoming) == 1
        user_id, sent_match_id, caller_id, caller_name, call_type = incoming[0]
        assert str(user_id) == a_id  # the callee being rung, not the caller
        assert str(caller_id) == b_id
        assert call_type == "video"


def test_video_call_offer_with_call_type_audio_is_relayed_and_reflected_in_the_push(monkeypatch):
    """Same as the test above, but exercises the new call_type="audio" path —
    added for the audio-calling feature (not just video)."""
    import app.routers.ws_chat as ws_chat

    incoming = []

    async def fake_send_incoming_call_notification(db, user_id, match_id, caller_id, caller_name, call_type="video"):
        incoming.append(call_type)

    monkeypatch.setattr(ws_chat.push_service, "send_incoming_call_notification", fake_send_incoming_call_notification)
    monkeypatch.setattr(ws_chat, "RING_TIMEOUT_SECONDS", 3600)

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vcAudio1@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vcAudio2@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json(
                    {"type": "call_offer", "match_id": match_id, "call_type": "audio", "sdp": "fake-offer-sdp"}
                )
                offer = ws_a.receive_json()
                assert offer["call_type"] == "audio"

                deadline = time.time() + 5
                while not incoming and time.time() < deadline:
                    time.sleep(0.1)
        assert incoming == ["audio"]


def test_video_call_unanswered_within_the_ring_window_times_out_and_sends_a_missed_call_push(monkeypatch):
    import app.routers.ws_chat as ws_chat

    monkeypatch.setattr(ws_chat, "RING_TIMEOUT_SECONDS", 0.2)
    missed = []

    async def fake_send_missed_call_notification(db, user_id, match_id, caller_id, caller_name):
        missed.append((user_id, match_id, caller_id, caller_name))

    monkeypatch.setattr(ws_chat.push_service, "send_missed_call_notification", fake_send_missed_call_notification)
    monkeypatch.setattr(ws_chat.push_service, "send_incoming_call_notification", _noop)

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc2e@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc2f@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_a.receive_json()
                call_id = offer["call_id"]
                # Neither side answers — after RING_TIMEOUT_SECONDS both get a
                # call_end("timeout") and A (the callee) gets a missed-call push.
                caller_ended = ws_b.receive_json()
                assert caller_ended == {"type": "call_end", "call_id": call_id, "reason": "timeout"}
                callee_ended = ws_a.receive_json()
                assert callee_ended == {"type": "call_end", "call_id": call_id, "reason": "timeout"}

                # Must poll *inside* both `with` blocks: the background ring-timeout
                # task's final await (the push) runs after both call_end sends, and
                # closing either socket can cancel it mid-flight (same anyio
                # cancel-scope behavior noted on the offline-peer test above).
                deadline = time.time() + 5
                while not missed and time.time() < deadline:
                    time.sleep(0.1)
        assert len(missed) == 1
        user_id, sent_match_id, caller_id, caller_name = missed[0]
        assert str(user_id) == a_id
        assert str(caller_id) == b_id


def test_video_call_answered_before_the_ring_window_does_not_time_out(monkeypatch):
    import app.routers.ws_chat as ws_chat

    monkeypatch.setattr(ws_chat, "RING_TIMEOUT_SECONDS", 0.3)
    monkeypatch.setattr(ws_chat.push_service, "send_incoming_call_notification", _noop)
    monkeypatch.setattr(
        ws_chat.push_service,
        "send_missed_call_notification",
        lambda *a, **k: pytest.fail("an answered call must not be treated as missed"),
    )

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc2g@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc2h@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_a.receive_json()
                call_id = offer["call_id"]
                ws_a.send_json({"type": "call_answer", "call_id": call_id, "sdp": "fake-answer-sdp"})
                ws_b.receive_json()  # the call_answer forwarded to B

                # Outlive the (short-circuited) ring window to prove the timeout
                # task correctly no-ops once the call is "active".
                time.sleep(1)


def test_disconnect_mid_call_notifies_peer():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc3a@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc3b@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                offer = ws_a.receive_json()
                call_id = offer["call_id"]
                ws_a.send_json({"type": "call_answer", "call_id": call_id, "sdp": "fake-answer-sdp"})
                ws_b.receive_json()  # the call_answer forwarded to B

                # Explicitly signal the disconnect and read the notification
                # here, before this `with` block's own __exit__ runs. Letting
                # __exit__ trigger the disconnect instead is racy: right
                # after closing, it also cancels the server-side task
                # group (WebSocketTestSession._notify_close ->
                # cancel_scope.cancel()), which can interrupt the
                # ws_chat() finally block's `await manager.send_to_user(...)`
                # before the notification actually reaches the peer — this hung
                # the peer's receive_json() forever until pytest-timeout caught it.
                # A real deployment doesn't have this race (uvicorn lets the
                # handler's own cleanup run to completion on disconnect).
                ws_b.close()
                ended = ws_a.receive_json()
                assert ended["type"] == "call_end"
                assert ended["reason"] == "peer_offline"


def test_disconnect_while_still_ringing_sends_the_callee_a_missed_call_push_once_they_reconnect(monkeypatch):
    """Distinct from test_disconnect_mid_call_notifies_peer: here the call was
    never answered (still "ringing", connected_at is None) when the callee's
    connection drops — a genuine missed call, unlike a disconnect mid-conversation."""
    import app.routers.ws_chat as ws_chat

    monkeypatch.setattr(ws_chat, "RING_TIMEOUT_SECONDS", 3600)
    monkeypatch.setattr(ws_chat.push_service, "send_incoming_call_notification", _noop)
    missed = []

    async def fake_send_missed_call_notification(db, user_id, match_id, caller_id, caller_name):
        missed.append((user_id, match_id, caller_id, caller_name))

    monkeypatch.setattr(ws_chat.push_service, "send_missed_call_notification", fake_send_missed_call_notification)

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "vc3c@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "vc3d@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        match_id = create_ordinary_match_sync(a_id, b_id)

        with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
            with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
                ws_b.send_json({"type": "call_offer", "match_id": match_id, "sdp": "fake-offer-sdp"})
                ws_a.receive_json()  # the offer — A never answers it
                ws_a.close()
                ended = ws_b.receive_json()
                assert ended["type"] == "call_end"
                assert ended["reason"] == "peer_offline"

                deadline = time.time() + 5
                while not missed and time.time() < deadline:
                    time.sleep(0.1)
        assert len(missed) == 1
        user_id, sent_match_id, caller_id, caller_name = missed[0]
        assert str(user_id) == a_id  # the callee who disconnected before answering
        assert str(caller_id) == b_id
