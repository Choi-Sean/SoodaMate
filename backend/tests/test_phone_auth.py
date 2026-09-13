import pytest

from tests.helpers import track_test_user


class FakeSmsVerifier:
    def __init__(self, valid_code="123456"):
        self.valid_code = valid_code
        self.started = []

    async def start(self, phone_number):
        self.started.append(phone_number)

    async def check(self, phone_number, code):
        return code == self.valid_code


@pytest.mark.asyncio
async def test_rejects_non_e164_phone_number(client, monkeypatch):
    import app.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "sms_verifier", FakeSmsVerifier())

    resp = await client.post("/auth/phone/start", json={"phone_number": "01098765001"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_confirm_with_wrong_code_rejected(client, monkeypatch):
    import app.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "sms_verifier", FakeSmsVerifier())

    resp = await client.post(
        "/auth/phone/confirm", json={"phone_number": "+821098765002", "code": "000000"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_new_phone_number_creates_account(client, monkeypatch):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(auth_router, "sms_verifier", fake)

    start = await client.post("/auth/phone/start", json={"phone_number": "+821098765003"})
    assert start.status_code == 204
    assert fake.started == ["+821098765003"]

    confirm = await client.post(
        "/auth/phone/confirm", json={"phone_number": "+821098765003", "code": "123456"}
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["is_new_user"] is True
    assert "access_token" in body
    track_test_user(body["user_id"])

    me = await client.get("/account/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["phone_verified"] is True


@pytest.mark.asyncio
async def test_returning_phone_number_logs_in_same_account(client, monkeypatch):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(auth_router, "sms_verifier", fake)

    first = await client.post(
        "/auth/phone/confirm", json={"phone_number": "+821098765004", "code": "123456"}
    )
    first_body = first.json()
    assert first_body["is_new_user"] is True
    track_test_user(first_body["user_id"])

    second = await client.post(
        "/auth/phone/confirm", json={"phone_number": "+821098765004", "code": "123456"}
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["is_new_user"] is False
    assert second_body["user_id"] == first_body["user_id"]
