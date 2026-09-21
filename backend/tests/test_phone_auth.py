import pytest

from app.config import settings
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


@pytest.mark.asyncio
async def test_dev_bypass_number_skips_real_sms_when_configured(client, monkeypatch):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier(valid_code="123456")
    monkeypatch.setattr(auth_router, "sms_verifier", fake)
    monkeypatch.setattr(settings, "dev_phone_bypass_numbers", "+821098765005")
    monkeypatch.setattr(settings, "dev_phone_bypass_code", "999111")

    start = await client.post("/auth/phone/start", json={"phone_number": "+821098765005"})
    assert start.status_code == 204
    assert fake.started == []  # never hit the real verifier, so no Twilio send/cost

    confirm = await client.post(
        "/auth/phone/confirm", json={"phone_number": "+821098765005", "code": "999111"}
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert "access_token" in body
    track_test_user(body["user_id"])


@pytest.mark.asyncio
async def test_dev_bypass_number_wrong_code_falls_through_to_real_check(client, monkeypatch):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier(valid_code="123456")
    monkeypatch.setattr(auth_router, "sms_verifier", fake)
    monkeypatch.setattr(settings, "dev_phone_bypass_numbers", "+821098765006")
    monkeypatch.setattr(settings, "dev_phone_bypass_code", "999111")

    # Wrong code for a listed number isn't specially handled — it falls
    # through to the real verifier (here, the fake) and fails normally,
    # exactly like any other number's wrong code.
    confirm = await client.post(
        "/auth/phone/confirm", json={"phone_number": "+821098765006", "code": "000000"}
    )
    assert confirm.status_code == 400


@pytest.mark.asyncio
async def test_dev_bypass_inert_when_code_not_configured(client, monkeypatch):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier(valid_code="123456")
    monkeypatch.setattr(auth_router, "sms_verifier", fake)
    monkeypatch.setattr(settings, "dev_phone_bypass_numbers", "+821098765007")
    # Explicit off (also the real default everywhere unconfigured).
    monkeypatch.setattr(settings, "dev_phone_bypass_code", "")

    # A listed number with no bypass code configured behaves like any other
    # number: start actually calls the real verifier.
    start = await client.post("/auth/phone/start", json={"phone_number": "+821098765007"})
    assert start.status_code == 204
    assert fake.started == ["+821098765007"]

    confirm = await client.post(
        "/auth/phone/confirm", json={"phone_number": "+821098765007", "code": "123456"}
    )
    assert confirm.status_code == 200
    track_test_user(confirm.json()["user_id"])


# --- Internet (VoIP) / virtual number filtering ------------------------------
# conftest stubs phone_screening._lookup_line_type for every test; grab the
# real one now (at import, before that per-test patch) for the parsing tests.
import httpx  # noqa: E402

from app.services import phone_screening  # noqa: E402

_REAL_LOOKUP = phone_screening._lookup_line_type
_REAL_ASYNC_CLIENT = httpx.AsyncClient

US_NUMBER = "+12135550142"


def _stub_line_type(monkeypatch, line_type):
    calls = []

    async def _lookup(phone_number):
        calls.append(phone_number)
        return line_type

    monkeypatch.setattr(phone_screening, "_lookup_line_type", _lookup)
    monkeypatch.setattr(settings, "twilio_account_sid", "ACtest")
    monkeypatch.setattr(settings, "twilio_auth_token", "token")
    monkeypatch.setattr(settings, "block_voip_phone_numbers", True)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize("number", ["+827012345678", "+8250212345678", "+82212345678"])
async def test_korean_non_mobile_numbers_rejected_without_any_lookup(client, monkeypatch, number):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(auth_router, "sms_verifier", fake)
    calls = _stub_line_type(monkeypatch, "mobile")

    resp = await client.post("/auth/phone/start", json={"phone_number": number})
    assert resp.status_code == 400
    assert resp.json()["detail"] == phone_screening.VIRTUAL_NUMBER_DETAIL
    assert fake.started == []
    assert calls == []  # free prefix rule, no paid Lookup


@pytest.mark.asyncio
@pytest.mark.parametrize("line_type", ["nonFixedVoip", "fixedVoip", "landline", "tollFree"])
async def test_voip_and_non_mobile_line_types_rejected(client, monkeypatch, line_type):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(auth_router, "sms_verifier", fake)
    _stub_line_type(monkeypatch, line_type)

    resp = await client.post("/auth/phone/start", json={"phone_number": US_NUMBER})
    assert resp.status_code == 400
    assert resp.json()["detail"] == phone_screening.VIRTUAL_NUMBER_DETAIL
    assert fake.started == []  # no SMS spent on a blocked number


@pytest.mark.asyncio
@pytest.mark.parametrize("line_type", ["mobile", "unknown", None])
async def test_mobile_and_unclassifiable_numbers_allowed(client, monkeypatch, line_type):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(auth_router, "sms_verifier", fake)
    _stub_line_type(monkeypatch, line_type)

    resp = await client.post("/auth/phone/start", json={"phone_number": US_NUMBER})
    assert resp.status_code == 204
    assert fake.started == [US_NUMBER]


@pytest.mark.asyncio
async def test_voip_filter_can_be_switched_off(client, monkeypatch):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(auth_router, "sms_verifier", fake)
    calls = _stub_line_type(monkeypatch, "nonFixedVoip")
    monkeypatch.setattr(settings, "block_voip_phone_numbers", False)

    resp = await client.post("/auth/phone/start", json={"phone_number": US_NUMBER})
    assert resp.status_code == 204
    assert calls == []


@pytest.mark.asyncio
async def test_existing_account_is_not_locked_out_by_voip_check(client, monkeypatch):
    import app.routers.auth as auth_router

    fake = FakeSmsVerifier()
    monkeypatch.setattr(auth_router, "sms_verifier", fake)

    # Account created while the number looked like a normal mobile...
    first = await client.post("/auth/phone/confirm", json={"phone_number": US_NUMBER, "code": "123456"})
    assert first.status_code == 200
    track_test_user(first.json()["user_id"])

    # ...and is later (mis)classified as VoIP: login must still work.
    calls = _stub_line_type(monkeypatch, "nonFixedVoip")
    resp = await client.post("/auth/phone/start", json={"phone_number": US_NUMBER})
    assert resp.status_code == 204
    assert calls == []


@pytest.mark.asyncio
async def test_dev_bypass_number_skips_voip_check(client, monkeypatch):
    import app.routers.auth as auth_router

    monkeypatch.setattr(auth_router, "sms_verifier", FakeSmsVerifier())
    calls = _stub_line_type(monkeypatch, "nonFixedVoip")
    monkeypatch.setattr(settings, "dev_phone_bypass_numbers", US_NUMBER)
    monkeypatch.setattr(settings, "dev_phone_bypass_code", "999111")

    resp = await client.post("/auth/phone/start", json={"phone_number": US_NUMBER})
    assert resp.status_code == 204
    assert calls == []


def _patch_lookup_http(monkeypatch, handler):
    monkeypatch.setattr(
        phone_screening.httpx,
        "AsyncClient",
        lambda **kw: _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kw),
    )
    monkeypatch.setattr(settings, "twilio_account_sid", "ACtest")
    monkeypatch.setattr(settings, "twilio_auth_token", "token")


@pytest.mark.asyncio
async def test_lookup_parses_line_type_and_encodes_number(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"line_type_intelligence": {"type": "nonFixedVoip", "error_code": None}})

    _patch_lookup_http(monkeypatch, handler)

    assert await _REAL_LOOKUP("+12135550142") == "nonFixedVoip"
    assert "/PhoneNumbers/%2B12135550142" in seen["url"]
    assert "Fields=line_type_intelligence" in seen["url"]


@pytest.mark.asyncio
async def test_lookup_fails_open_on_http_error_and_error_code(monkeypatch):
    _patch_lookup_http(monkeypatch, lambda request: httpx.Response(403, json={"message": "not enabled"}))
    assert await _REAL_LOOKUP("+12135550142") is None

    _patch_lookup_http(
        monkeypatch,
        lambda request: httpx.Response(200, json={"line_type_intelligence": {"type": None, "error_code": 60600}}),
    )
    assert await _REAL_LOOKUP("+12135550142") is None
