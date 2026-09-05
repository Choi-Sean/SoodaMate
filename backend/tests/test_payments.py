import pytest

from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_products_listed(client):
    resp = await client.get("/payments/products")
    assert resp.status_code == 200
    ids = [p["product_id"] for p in resp.json()]
    assert "superlike_pack_5" in ids
    assert "boost_1" in ids


@pytest.mark.asyncio
async def test_checkout_session_requires_configured_stripe(client):
    _, headers = await create_user_with_profile(client, "pay1@example.com")
    # No STRIPE_SECRET_KEY configured in test env -> fails loudly, not silently.
    resp = await client.post(
        "/payments/create-checkout-session", headers=headers, json={"product_id": "boost_1"}
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_webhook_grants_credits_and_is_idempotent(client, monkeypatch):
    import app.services.payment_service as payment_service

    user_id, headers = await create_user_with_profile(client, "pay2@example.com")
    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", "whsec_fake")

    fake_event = {
        "id": "evt_test_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_1",
                "metadata": {"user_id": user_id, "product_id": "superlike_pack_5"},
            }
        },
    }
    monkeypatch.setattr(
        payment_service.stripe.Webhook, "construct_event", lambda *a, **kw: fake_event
    )

    resp = await client.post("/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"})
    assert resp.status_code == 204

    balance = await client.get("/payments/balance", headers=headers)
    assert balance.json()["superlike_credits"] == 5

    # Redelivery of the same event must not double-grant credits.
    resp2 = await client.post("/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"})
    assert resp2.status_code == 204
    balance2 = await client.get("/payments/balance", headers=headers)
    assert balance2.json()["superlike_credits"] == 5


@pytest.mark.asyncio
async def test_activate_boost_requires_credits(client):
    _, headers = await create_user_with_profile(client, "pay3@example.com")
    resp = await client.post("/payments/activate-boost", headers=headers)
    assert resp.status_code == 402


@pytest.mark.asyncio
async def test_activate_boost_consumes_credit(client, monkeypatch):
    import app.services.payment_service as payment_service

    user_id, headers = await create_user_with_profile(client, "pay4@example.com")
    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", "whsec_fake")

    fake_event = {
        "id": "evt_test_2",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_2", "metadata": {"user_id": user_id, "product_id": "boost_1"}}},
    }
    monkeypatch.setattr(payment_service.stripe.Webhook, "construct_event", lambda *a, **kw: fake_event)
    await client.post("/payments/webhook", content=b"{}", headers={"stripe-signature": "sig"})

    resp = await client.post("/payments/activate-boost", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["boost_active_until"] is not None

    balance = await client.get("/payments/balance", headers=headers)
    assert balance.json()["boost_credits"] == 0
