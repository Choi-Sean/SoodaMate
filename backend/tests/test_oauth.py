import pytest

from app.core.auth_provider_base import ExternalIdentity
from app.routers import auth as auth_router


@pytest.mark.asyncio
async def test_google_login_creates_user_then_reuses_identity(client, monkeypatch):
    async def fake_verify(token: str) -> ExternalIdentity:
        return ExternalIdentity(provider_user_id="google-uid-1", email="g@example.com", raw_claims={})

    monkeypatch.setattr(auth_router.google_verifier, "verify", fake_verify)

    resp1 = await client.post("/auth/google", json={"id_token": "whatever"})
    assert resp1.status_code == 200
    user_id_1 = resp1.json()["user_id"]

    resp2 = await client.post("/auth/google", json={"id_token": "whatever-again"})
    assert resp2.status_code == 200
    assert resp2.json()["user_id"] == user_id_1


@pytest.mark.asyncio
async def test_kakao_login_creates_user(client, monkeypatch):
    async def fake_verify(token: str) -> ExternalIdentity:
        return ExternalIdentity(provider_user_id="kakao-uid-1", email=None, raw_claims={})

    monkeypatch.setattr(auth_router.kakao_verifier, "verify", fake_verify)

    resp = await client.post("/auth/kakao", json={"access_token": "whatever"})
    assert resp.status_code == 200
    assert "user_id" in resp.json()


@pytest.mark.asyncio
async def test_google_login_invalid_token_rejected(client, monkeypatch):
    async def fake_verify(token: str) -> ExternalIdentity:
        raise ValueError("bad token")

    monkeypatch.setattr(auth_router.google_verifier, "verify", fake_verify)

    resp = await client.post("/auth/google", json={"id_token": "bad"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_apple_login_creates_user_then_reuses_identity(client, monkeypatch):
    async def fake_verify(token: str) -> ExternalIdentity:
        return ExternalIdentity(provider_user_id="apple-uid-1", email="a@example.com", raw_claims={})

    monkeypatch.setattr(auth_router.apple_verifier, "verify", fake_verify)

    resp1 = await client.post("/auth/apple", json={"identity_token": "whatever"})
    assert resp1.status_code == 200
    user_id_1 = resp1.json()["user_id"]

    # Apple only includes email on the very first sign-in for this app;
    # subsequent identityTokens omit it — must still resolve to the same user.
    async def fake_verify_no_email(token: str) -> ExternalIdentity:
        return ExternalIdentity(provider_user_id="apple-uid-1", email=None, raw_claims={})

    monkeypatch.setattr(auth_router.apple_verifier, "verify", fake_verify_no_email)

    resp2 = await client.post("/auth/apple", json={"identity_token": "whatever-again"})
    assert resp2.status_code == 200
    assert resp2.json()["user_id"] == user_id_1


@pytest.mark.asyncio
async def test_apple_login_invalid_token_rejected(client, monkeypatch):
    async def fake_verify(token: str) -> ExternalIdentity:
        raise ValueError("bad token")

    monkeypatch.setattr(auth_router.apple_verifier, "verify", fake_verify)

    resp = await client.post("/auth/apple", json={"identity_token": "bad"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_google_and_email_signup_with_same_address_link_to_one_account(client, monkeypatch):
    signup = await client.post("/auth/signup", json={"email": "shared@example.com", "password": "password123"})
    email_user_id = signup.json()["user_id"]

    async def fake_verify(token: str) -> ExternalIdentity:
        return ExternalIdentity(provider_user_id="google-uid-2", email="shared@example.com", raw_claims={})

    monkeypatch.setattr(auth_router.google_verifier, "verify", fake_verify)

    resp = await client.post("/auth/google", json={"id_token": "whatever"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == email_user_id
