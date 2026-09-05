import pytest


@pytest.mark.asyncio
async def test_signup_then_login(client):
    resp = await client.post("/auth/signup", json={"email": "a@example.com", "password": "password123"})
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body

    resp = await client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == body["user_id"]


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(client):
    await client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    resp = await client.post("/auth/signup", json={"email": "dup@example.com", "password": "password123"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    await client.post("/auth/signup", json={"email": "b@example.com", "password": "password123"})
    resp = await client.post("/auth/login", json={"email": "b@example.com", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_issues_new_access_token(client):
    signup = await client.post("/auth/signup", json={"email": "c@example.com", "password": "password123"})
    refresh_token = signup.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_access_token_used_as_refresh_is_rejected(client):
    signup = await client.post("/auth/signup", json={"email": "d@example.com", "password": "password123"})
    access_token = signup.json()["access_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": access_token})
    assert resp.status_code == 401
