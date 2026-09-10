import json

import pytest
import stripe

from tests.helpers import create_user_with_profile

_WEBHOOK_SECRET = "whsec_testsecret_0123456789abcdef"


def _webhook_post_args(event: dict) -> dict:
    """Build a real, correctly-signed webhook request the same way Stripe
    would — so the handler runs its true construct_event + payload-parse
    path (a fake dict return from construct_event used to hide bugs in it)."""
    payload = json.dumps(event)
    sig = stripe.WebhookSignature.generate_signature_header(payload, _WEBHOOK_SECRET)
    return {"content": payload.encode(), "headers": {"stripe-signature": sig}}


def _checkout_completed(evt_id: str, session_id: str, user_id: str, product_id: str) -> dict:
    obj = {"id": session_id, "object": "checkout.session", "metadata": {"user_id": user_id, "product_id": product_id}}
    if "membership" in product_id:
        obj["subscription"] = "sub_test_123"
    return {
        "id": evt_id,
        "object": "event",
        "type": "checkout.session.completed",
        "data": {"object": obj},
    }


@pytest.mark.asyncio
async def test_products_listed(client):
    resp = await client.get("/payments/products")
    assert resp.status_code == 200
    ids = [p["product_id"] for p in resp.json()]
    assert "superlike_pack_5" in ids
    assert "boost_1" in ids


@pytest.mark.asyncio
async def test_checkout_session_requires_configured_stripe(client, monkeypatch):
    import app.services.payment_service as payment_service

    _, headers = await create_user_with_profile(client, "pay1@example.com")
    # Explicitly unset rather than relying on the ambient .env not having a
    # real key configured — this test's whole premise (Stripe unconfigured
    # -> fails loudly, not silently) silently stopped holding the moment a
    # real STRIPE_SECRET_KEY was added to .env for live testing.
    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "")
    resp = await client.post(
        "/payments/create-checkout-session", headers=headers, json={"product_id": "boost_1"}
    )
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_webhook_grants_credits_and_is_idempotent(client, monkeypatch):
    import app.services.payment_service as payment_service

    user_id, headers = await create_user_with_profile(client, "pay2@example.com")
    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)

    event = _checkout_completed("evt_pay2_1", "cs_pay2_1", user_id, "superlike_pack_5")
    resp = await client.post("/payments/webhook", **_webhook_post_args(event))
    assert resp.status_code == 204, resp.text

    balance = await client.get("/payments/balance", headers=headers)
    assert balance.json()["superlike_credits"] == 5

    # Redelivery of the same event must not double-grant credits.
    resp2 = await client.post("/payments/webhook", **_webhook_post_args(event))
    assert resp2.status_code == 204
    balance2 = await client.get("/payments/balance", headers=headers)
    assert balance2.json()["superlike_credits"] == 5


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(client, monkeypatch):
    import app.services.payment_service as payment_service

    user_id, _ = await create_user_with_profile(client, "pay-badsig@example.com")
    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)

    event = _checkout_completed("evt_bad_1", "cs_bad_1", user_id, "superlike_pack_5")
    resp = await client.post(
        "/payments/webhook",
        content=json.dumps(event).encode(),
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_grants_membership(client, monkeypatch):
    import app.services.payment_service as payment_service

    user_id, headers = await create_user_with_profile(client, "pay-mem@example.com")
    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)

    event = _checkout_completed("evt_mem_1", "cs_mem_1", user_id, "membership_monthly")
    resp = await client.post("/payments/webhook", **_webhook_post_args(event))
    assert resp.status_code == 204

    me = await client.get("/profiles/me", headers=headers)
    body = me.json()
    assert body["is_premium_member"] is True
    assert body["billing_cycle"] == "monthly"


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
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)

    event = _checkout_completed("evt_pay4_1", "cs_pay4_1", user_id, "boost_1")
    await client.post("/payments/webhook", **_webhook_post_args(event))

    resp = await client.post("/payments/activate-boost", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["boost_active_until"] is not None

    balance = await client.get("/payments/balance", headers=headers)
    assert balance.json()["boost_credits"] == 0
