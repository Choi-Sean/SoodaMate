"""Fast unit tests for the security building blocks (no database, no network)."""
import asyncio
import base64
import time
import uuid

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.config import settings
from app.core import rate_limit
from app.core.user_lock import user_lock
from app.main import create_app, validate_production_settings
from app.services import ad_ssv_service, storage_service


@pytest.fixture(autouse=True)
def _limiter_on(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    rate_limit.reset()
    yield
    rate_limit.reset()


def test_rate_limit_blocks_after_limit_and_reports_retry_after():
    for _ in range(3):
        rate_limit.enforce("unit", "k", 3, 60)
    with pytest.raises(HTTPException) as exc:
        rate_limit.enforce("unit", "k", 3, 60)
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) >= 1
    rate_limit.enforce("unit", "another-key", 3, 60)  # keys are independent


def test_rate_limit_cost_is_weighted_and_disabled_flag_bypasses(monkeypatch):
    assert rate_limit.allow("budget", "u", 100, 60, cost=60)
    assert not rate_limit.allow("budget", "u", 100, 60, cost=60)
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    assert rate_limit.allow("budget", "u", 100, 60, cost=60)


def test_rate_limit_window_expires():
    assert rate_limit._hit("w", 1, 1, 1) is None
    assert rate_limit._hit("w", 1, 1, 1) is not None
    time.sleep(1.1)
    assert rate_limit._hit("w", 1, 1, 1) is None


class _Req:
    def __init__(self, xff=None, host="9.9.9.9"):
        self.headers = {"x-forwarded-for": xff} if xff else {}
        self.client = type("C", (), {"host": host})()


def test_client_ip_ignores_forged_left_entries(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert rate_limit.client_ip(_Req("1.2.3.4, 5.6.7.8")) == "5.6.7.8"
    assert rate_limit.client_ip(_Req(None)) == "9.9.9.9"
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    assert rate_limit.client_ip(_Req("1.2.3.4, 5.6.7.8")) == "1.2.3.4"


@pytest.mark.asyncio
async def test_user_lock_serializes_read_modify_write():
    balance = {"credits": 1, "spent": 0}

    async def spend():
        async with user_lock("credits:test"):
            have = balance["credits"]
            await asyncio.sleep(0.01)  # a request that yields between read and write
            if have > 0:
                balance["credits"] = have - 1
                balance["spent"] += 1

    await asyncio.gather(*[spend() for _ in range(8)])
    assert balance == {"credits": 0, "spent": 1}


def test_object_path_validation_is_strict():
    uid, other = uuid.uuid4(), uuid.uuid4()
    name = f"{uuid.uuid4()}.jpg"
    good = f"users/{uid}/photos/{name}"
    assert storage_service.is_valid_user_object_path(good, uid, "photos")
    assert not storage_service.is_valid_user_object_path(good, uid, "chat")
    assert not storage_service.is_valid_user_object_path(good, other, "photos")
    for bad in (
        f"users/{uid}/photos/../../{other}/photos/{name}",
        f"users/{uid}/photos//{name}",
        f"users/{uid}/photos/{name}/../{name}",
        f"users/{uid}/photos/anything.jpg",
        f"verifications/{uid}/selfie-{name}",
        f"users/{uid}/photos/{name}.exe",
        "",
    ):
        assert not storage_service.is_valid_user_object_path(bad, uid, "photos"), bad


def test_magic_bytes_match_declared_type():
    assert storage_service._magic_ok("jpg", bytes([0xFF, 0xD8, 0xFF, 0xE0]))
    assert not storage_service._magic_ok("jpg", b"<html><script>")
    assert storage_service._magic_ok("png", bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]))
    assert storage_service._magic_ok("webp", b"RIFF\x00\x00\x00\x00WEBP")
    assert storage_service._magic_ok("mp4", b"\x00\x00\x00\x18ftypmp42")
    assert storage_service._magic_ok("mp4", b"\x00\x00\x00\x08wide\x00\x00")  # older QuickTime .mov
    assert storage_service._magic_ok("mp4", b"\x00\x00\x00\x08moov\x00\x00")
    assert not storage_service._magic_ok("mp4", b"<html><body>")
    assert storage_service.MAX_IMAGE_BYTES >= 20 * 1024 * 1024 and storage_service.MAX_VIDEO_BYTES >= 100 * 1024 * 1024
    # a PNG/WebP handed back by the OS picker under the app's fixed image/jpeg label is still a photo
    assert storage_service._magic_ok("jpg", bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]))
    assert storage_service._magic_ok("png", bytes([0xFF, 0xD8, 0xFF]))
    for ext in ("jpg", "png", "webp"):
        assert not storage_service._magic_ok(ext, b"<html><script>")
        assert not storage_service._magic_ok(ext, b"MZ\x90\x00")  # Windows executable


def test_production_settings_guard():
    from app.config import Settings

    with pytest.raises(RuntimeError):
        validate_production_settings(Settings(app_env="production", secret_key="dev-secret-key-not-for-production"))
    with pytest.raises(RuntimeError):
        validate_production_settings(Settings(app_env="production", secret_key="short"))
    with pytest.raises(RuntimeError):
        validate_production_settings(
            Settings(app_env="production", secret_key="x" * 40, database_url="mssql://sa:ChangeMe123!@h/d")
        )
    with pytest.raises(RuntimeError):
        validate_production_settings(
            Settings(app_env="production", secret_key="x" * 40, database_url="mssql://u:p@h/d", cors_origins="*")
        )
    validate_production_settings(
        Settings(app_env="production", secret_key="x" * 40, database_url="mssql://u:p@h/d", cors_origins="https://a.b")
    )


def test_production_app_hides_docs_and_sets_headers():
    from starlette.testclient import TestClient

    with TestClient(create_app(production=True)) as tc:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert tc.get(path).status_code == 404
        r = tc.get("/health")
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "max-age" in r.headers["strict-transport-security"]
        assert r.headers["x-frame-options"] == "DENY"
    with TestClient(create_app(production=False)) as tc:
        assert tc.get("/docs").status_code == 200


def test_oversized_body_is_refused_before_parsing(monkeypatch):
    from starlette.testclient import TestClient

    monkeypatch.setattr(settings, "max_json_body_bytes", 1000)
    with TestClient(create_app(production=False)) as tc:
        r = tc.post("/auth/login", content=b"x" * 5000, headers={"content-type": "application/json"})
        assert r.status_code == 413
        assert tc.get("/health").status_code == 200


# ------------------------------------------------ AdMob server-side verification (signature logic)


def _signed_query(key, unit, user_id, ts_ms=None, tamper=False, custom_data=None):
    ts_ms = ts_ms or int(time.time() * 1000)
    query = (
        f"ad_network=5450213213286189855&ad_unit={unit}&reward_amount=1&reward_item=bonus"
        f"&timestamp={ts_ms}&transaction_id={uuid.uuid4().hex}&user_id={user_id}"
    )
    if custom_data:
        query += f"&custom_data={custom_data}"
    sig = base64.urlsafe_b64encode(key.sign(query.encode(), ec.ECDSA(hashes.SHA256()))).decode().rstrip("=")
    if tamper:
        query = query.replace("reward_amount=1", "reward_amount=99")
    return f"{query}&signature={sig}&key_id=42"


class _FakeProfile:
    blind_chat_bonus_ad_watched_on = None
    swipe_bonus_ad_watched_on = None


class _FakeDb:
    def __init__(self, profile):
        self.profile, self.commits = profile, 0

    async def get(self, _model, _pk):
        return self.profile

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_ssv_verifies_signature_unit_age_and_user(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    ad_ssv_service.set_test_keys({"42": pem})
    unit = "ca-app-pub-1111111111111111/2222222222"
    monkeypatch.setattr(settings, "admob_rewarded_unit_ids", unit)
    uid = str(uuid.uuid4())
    try:
        async def call(query, profile=None):
            db = _FakeDb(profile if profile is not None else _FakeProfile())
            await ad_ssv_service.verify_and_grant(db, query)
            return db

        db = await call(_signed_query(key, unit, uid))
        assert db.profile.blind_chat_bonus_ad_watched_on is not None and db.commits == 1

        for label, query in {
            "tampered": _signed_query(key, unit, uid, tamper=True),
            "wrong key": _signed_query(ec.generate_private_key(ec.SECP256R1()), unit, uid),
            "someone else's ad unit": _signed_query(key, "ca-app-pub-9999999999999999/1", uid),
            "stale": _signed_query(key, unit, uid, ts_ms=int((time.time() - 3600) * 1000)),
            "no signature": "ad_unit=x&user_id=y",
            "bad user id": _signed_query(key, unit, "not-a-uuid"),
        }.items():
            with pytest.raises(HTTPException) as exc:
                await call(query)
            assert exc.value.status_code in (400, 403), label

        monkeypatch.setattr(settings, "admob_rewarded_unit_ids", "")
        with pytest.raises(HTTPException):  # no pinned units configured => nothing is accepted
            await call(_signed_query(key, unit, uid))
    finally:
        ad_ssv_service.set_test_keys(None)


@pytest.mark.asyncio
async def test_ssv_custom_data_routes_to_the_right_bonus(monkeypatch):
    """One SSV callback endpoint serves two different rewarded-ad placements
    (Blind Chat's extra match, the swipe limit's extra swipe) — custom_data
    is how the signed callback says which one this ad was for. Missing/
    unrecognized custom_data must fall back to blind_chat, not swipe, so an
    older client build that never sends it keeps working unchanged."""
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    ad_ssv_service.set_test_keys({"42": pem})
    unit = "ca-app-pub-1111111111111111/2222222222"
    monkeypatch.setattr(settings, "admob_rewarded_unit_ids", unit)
    uid = str(uuid.uuid4())
    try:
        db_swipe = _FakeDb(_FakeProfile())
        await ad_ssv_service.verify_and_grant(db_swipe, _signed_query(key, unit, uid, custom_data="swipe"))
        assert db_swipe.profile.swipe_bonus_ad_watched_on is not None
        assert db_swipe.profile.blind_chat_bonus_ad_watched_on is None

        db_default = _FakeDb(_FakeProfile())
        await ad_ssv_service.verify_and_grant(db_default, _signed_query(key, unit, uid))
        assert db_default.profile.blind_chat_bonus_ad_watched_on is not None
        assert db_default.profile.swipe_bonus_ad_watched_on is None
    finally:
        ad_ssv_service.set_test_keys(None)


def test_candidate_distance_is_snapped_to_a_grid_and_rounded():
    """Trilateration defence: the other person is snapped to a ~2 km grid and the
    distance is shown in whole km, so measuring from self-chosen points can't
    locate them any better than their grid cell."""
    from app.services import discovery_service as d

    assert d._coarse(37.5695) == 37.56
    assert d._coarse(126.9705) == 126.98
    assert d._display_distance_km(None) is None
    assert d._display_distance_km(0.2) == 1.0
    assert d._display_distance_km(3.6) == 4.0
    seoul_to_busan = d._haversine_py(37.5665, 126.9780, 35.1796, 129.0756)
    assert 320 < seoul_to_busan < 335


def test_verification_photos_go_to_the_private_bucket_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "r2_bucket_name", "public-bucket")
    uid = uuid.uuid4()
    selfie = f"verifications/{uid}/selfie-{uuid.uuid4()}.jpg"
    photo = f"users/{uid}/photos/{uuid.uuid4()}.jpg"

    monkeypatch.setattr(settings, "r2_private_bucket_name", "")
    assert storage_service.bucket_for(selfie) == "public-bucket"  # unchanged default

    monkeypatch.setattr(settings, "r2_private_bucket_name", "private-bucket")
    assert storage_service.bucket_for(selfie) == "private-bucket"
    assert storage_service.bucket_for(photo) == "public-bucket"  # profile photos stay public

    calls = []

    class FakeClient:
        def list_objects_v2(self, **kw):
            calls.append(("list", kw["Bucket"]))
            return {"Contents": [{"Key": "k"}], "IsTruncated": False}

        def delete_object(self, **kw):
            calls.append(("delete", kw["Bucket"]))

    monkeypatch.setattr(storage_service, "_get_client", lambda: FakeClient())
    assert storage_service.delete_prefix(f"verifications/{uid}/") == 2  # swept from BOTH buckets
    assert {b for _, b in calls} == {"public-bucket", "private-bucket"}


def test_chunked_body_without_content_length_is_also_cut_off(monkeypatch):
    from starlette.testclient import TestClient

    monkeypatch.setattr(settings, "max_json_body_bytes", 1000)

    def chunks():
        for _ in range(10):
            yield b"x" * 500

    with TestClient(create_app(production=False)) as tc:
        r = tc.post("/auth/login", content=chunks(), headers={"content-type": "application/json"})
        assert r.status_code in (400, 413)
