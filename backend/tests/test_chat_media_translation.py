from datetime import date

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
        json={"gcs_object_path": f"users/{tokens['user_id']}/photos/0.jpg", "position": 0},
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
