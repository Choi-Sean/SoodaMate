import uuid
from datetime import date

import pytest
from starlette.testclient import TestClient

from app.main import app
from tests.helpers import track_test_user


def _signup_and_complete_profile(
    client: TestClient, email: str, gender: str, interested_in: str, preferred_language: str | None = None
) -> tuple[str, str]:
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
    if preferred_language:
        client.put("/account/language", headers=headers, json={"language": preferred_language})
    return tokens["user_id"], tokens["access_token"]


def test_image_message_round_trips_with_image_url():
    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "mediaA@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "mediaB@example.com", "female", "male")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        presign = tc.post(
            "/uploads/presign-chat-image", headers=b_headers, json={"content_type": "image/jpeg"}
        )
        assert presign.status_code == 200
        object_path = presign.json()["gcs_object_path"]
        assert object_path.startswith(f"users/{b_id}/chat/")

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # B is the female half of a mixed pair — allowed to send first
                # under Phase 14's Bumble rule.
                ws_b.send_json(
                    {
                        "type": "message",
                        "match_id": match_id,
                        "message_type": "image",
                        "image_object_path": object_path,
                    }
                )
                received = ws_a.receive_json()
                assert received["message_type"] == "image"
                assert received["image_url"] is not None
                assert object_path in received["image_url"]

        history = tc.get(f"/matches/{match_id}/messages", headers=a_headers)
        image_messages = [m for m in history.json() if m["message_type"] == "image"]
        assert len(image_messages) == 1
        assert image_messages[0]["image_url"] is not None


def test_chat_message_is_translated_when_languages_differ(monkeypatch):
    import app.services.translation_service as translation_service

    async def fake_translate(text, target_lang, source_lang=None):
        return f"[{target_lang}] {text}"

    monkeypatch.setattr(translation_service, "translate", fake_translate)

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(
            tc, "translateA@example.com", "male", "female", preferred_language="ko"
        )
        b_id, b_token = _signup_and_complete_profile(
            tc, "translateB@example.com", "female", "male", preferred_language="en"
        )
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_resp = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id})
        match_id = match_resp.json()["match_id"]

        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                # B (female half of a mixed pair) sends first.
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "hello"})
                received = ws_a.receive_json()
                assert received["content"] == "hello"
                assert received["translated_content"] == "[ko] hello"
                assert received["translated_language"] == "ko"
                assert received["original_language"] == "en"
                message_id = received["message_id"]

        # On-demand translate: either side, any of the 5 app languages, not just
        # the recipient's saved preferred_language.
        r = tc.post(
            f"/matches/{match_id}/messages/{message_id}/translate",
            headers=a_headers,
            json={"target_language": "es"},
        )
        assert r.status_code == 200, r.text
        assert r.json() == {"translated_content": "[es] hello", "target_language": "es"}


def test_translate_message_endpoint_rejects_bad_language_and_foreign_match(monkeypatch):
    import app.services.translation_service as translation_service

    monkeypatch.setattr(translation_service, "translate", lambda *a, **k: pytest.fail("must not be called"))

    with TestClient(app) as tc:
        a_id, a_token = _signup_and_complete_profile(tc, "translateC@example.com", "male", "female")
        b_id, b_token = _signup_and_complete_profile(tc, "translateD@example.com", "female", "male")
        outsider_id, outsider_token = _signup_and_complete_profile(tc, "translateE@example.com", "male", "female")
        a_headers = {"Authorization": f"Bearer {a_token}"}
        b_headers = {"Authorization": f"Bearer {b_token}"}
        outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

        tc.post("/interactions/like", headers=a_headers, json={"to_user_id": b_id})
        match_id = tc.post("/interactions/like", headers=b_headers, json={"to_user_id": a_id}).json()["match_id"]
        with tc.websocket_connect(f"/ws/chat?token={a_token}") as ws_a:
            with tc.websocket_connect(f"/ws/chat?token={b_token}") as ws_b:
                ws_b.send_json({"type": "message", "match_id": match_id, "content": "hi"})
                message_id = ws_a.receive_json()["message_id"]  # send_to_user only reaches the peer, not the sender

        bad_lang = tc.post(
            f"/matches/{match_id}/messages/{message_id}/translate", headers=a_headers, json={"target_language": "fr"}
        )
        assert bad_lang.status_code == 422

        not_a_participant = tc.post(
            f"/matches/{match_id}/messages/{message_id}/translate",
            headers=outsider_headers,
            json={"target_language": "ko"},
        )
        assert not_a_participant.status_code == 404

        wrong_match = tc.post(
            f"/matches/{uuid.uuid4()}/messages/{message_id}/translate", headers=a_headers, json={"target_language": "ko"}
        )
        assert wrong_match.status_code == 404
