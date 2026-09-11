import pytest

from tests.helpers import create_user_with_profile, track_test_user


class FakeSmsVerifier:
    def __init__(self, valid_code="123456"):
        self.valid_code = valid_code
        self.started = []

    async def start(self, phone_number):
        self.started.append(phone_number)

    async def check(self, phone_number, code):
        return code == self.valid_code


@pytest.mark.asyncio
async def test_start_fails_loudly_when_twilio_unconfigured(client, monkeypatch):
    # A real Twilio account is now configured in this env (see config.py),
    # so force the unconfigured branch directly rather than relying on
    # ambient env state — proves TwilioVerifySmsVerifier.start() 503s
    # honestly instead of pretending to send a code, same convention as
    # SmtpEmailSender.send()/payment_service._get_stripe().
    from app.services.sms import twilio_verify as twilio_verify_module

    monkeypatch.setattr(twilio_verify_module.settings, "twilio_account_sid", "")

    _, headers = await create_user_with_profile(client, "phoneverify1@example.com")
    resp = await client.post("/verification/phone/start", headers=headers, json={"phone_number": "+821012340001"})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_rejects_non_e164_phone_number(client, monkeypatch):
    import app.routers.verification as verification_router

    monkeypatch.setattr(verification_router, "sms_verifier", FakeSmsVerifier())

    _, headers = await create_user_with_profile(client, "phoneverify2@example.com")
    resp = await client.post("/verification/phone/start", headers=headers, json={"phone_number": "01012340002"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_full_phone_verification_flow_with_mocked_verifier(client, monkeypatch):
    import app.routers.verification as verification_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(verification_router, "sms_verifier", fake)

    _, headers = await create_user_with_profile(client, "phoneverify3@example.com")
    start = await client.post("/verification/phone/start", headers=headers, json={"phone_number": "+821012340003"})
    assert start.status_code == 204
    assert fake.started == ["+821012340003"]

    wrong = await client.post(
        "/verification/phone/confirm", headers=headers, json={"phone_number": "+821012340003", "code": "000000"}
    )
    assert wrong.status_code == 400

    confirm = await client.post(
        "/verification/phone/confirm", headers=headers, json={"phone_number": "+821012340003", "code": "123456"}
    )
    assert confirm.status_code == 204

    me = await client.get("/account/me", headers=headers)
    assert me.json()["phone_verified"] is True


@pytest.mark.asyncio
async def test_phone_number_already_verified_on_another_account_is_rejected(client, monkeypatch):
    import app.routers.verification as verification_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(verification_router, "sms_verifier", fake)

    _, headers_a = await create_user_with_profile(client, "phoneverify4a@example.com")
    await client.post("/verification/phone/start", headers=headers_a, json={"phone_number": "+821012340004"})
    confirm_a = await client.post(
        "/verification/phone/confirm", headers=headers_a, json={"phone_number": "+821012340004", "code": "123456"}
    )
    assert confirm_a.status_code == 204

    _, headers_b = await create_user_with_profile(client, "phoneverify4b@example.com")
    start_b = await client.post("/verification/phone/start", headers=headers_b, json={"phone_number": "+821012340004"})
    assert start_b.status_code == 409


@pytest.mark.asyncio
async def test_phone_verification_works_before_any_profile_exists(client, monkeypatch):
    """Signup now gates on phone verification *before* ProfileSetupScreen —
    /account/me and /verification/phone/* must work for a bare signed-up
    account that has no Profile row yet (unlike /profiles/me, which 404s)."""
    import app.routers.verification as verification_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(verification_router, "sms_verifier", fake)

    signup = await client.post("/auth/signup", json={"email": "phoneverify5@example.com", "password": "password123"})
    tokens = signup.json()
    track_test_user(tokens["user_id"])
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    me_before = await client.get("/account/me", headers=headers)
    assert me_before.status_code == 200
    assert me_before.json()["phone_verified"] is False

    await client.post("/verification/phone/start", headers=headers, json={"phone_number": "+821012340005"})
    confirm = await client.post(
        "/verification/phone/confirm", headers=headers, json={"phone_number": "+821012340005", "code": "123456"}
    )
    assert confirm.status_code == 204

    me_after = await client.get("/account/me", headers=headers)
    assert me_after.json()["phone_verified"] is True
