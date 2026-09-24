import json
import uuid as uuid_mod

import pytest
import stripe

from tests.helpers import create_user_with_profile

_WEBHOOK_SECRET = "whsec_testsecret_0123456789abcdef"

pytestmark = pytest.mark.asyncio


async def _make_admin(user_id: str) -> None:
    from app.database import async_session_factory
    from app.models.user import User

    async with async_session_factory() as session:
        user = await session.get(User, uuid_mod.UUID(user_id))
        user.is_admin = True
        await session.commit()


async def _send_checkout_completed(client, monkeypatch, user_id: str, product_id: str, amount_total_cents: int, event_id: str):
    import app.services.payment_service as payment_service

    monkeypatch.setattr(payment_service.settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(payment_service.settings, "stripe_webhook_secret", _WEBHOOK_SECRET)
    event = {
        "id": event_id,
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{event_id}",
                "object": "checkout.session",
                "amount_total": amount_total_cents,
                "metadata": {"user_id": user_id, "product_id": product_id},
            }
        },
    }
    payload = json.dumps(event)
    sig = stripe.WebhookSignature.generate_signature_header(payload, _WEBHOOK_SECRET)
    resp = await client.post("/payments/webhook", content=payload.encode(), headers={"stripe-signature": sig})
    assert resp.status_code == 204, resp.text


async def test_non_admin_cannot_read_dashboard_stats(client):
    _, headers = await create_user_with_profile(client, "notadmin@example.com")
    resp = await client.get("/admin/stats", headers=headers)
    assert resp.status_code == 403


async def test_30_day_revenue_reflects_actual_discounted_charge_not_list_price(client, monkeypatch):
    """Regression test: the dashboard used to sum PRODUCTS[product_id]
    ["price_usd_cents"] (the undiscounted list price) for every recent
    transaction, so a promo-discounted purchase (e.g. 50% off) inflated the
    reported revenue to the full price nobody actually paid. It must now
    reflect the real Stripe amount_total captured in each transaction's
    stored webhook payload (see routers/admin.py::_actual_amount_cents)."""
    admin_id, admin_headers = await create_user_with_profile(client, "admin_revenue@example.com")
    await _make_admin(admin_id)

    # Delta against whatever the shared DB already had in the last 30 days
    # (this runs against the real production database — see reference_qa_
    # suite conventions — so other real transactions may already be in
    # that window) rather than an exact total, so this test is robust to
    # pre-existing data.
    before = (await client.get("/admin/stats", headers=admin_headers)).json()["total_revenue_cents_30d"]

    buyer_id, _ = await create_user_with_profile(client, "buyer_revenue@example.com")
    # blind_peek_1 lists at 299 cents ($2.99); actually charged 150 (50% off,
    # e.g. via an active Promotion) — the list price must NOT appear anywhere
    # in the revenue total.
    await _send_checkout_completed(
        client, monkeypatch, buyer_id, "blind_peek_1", amount_total_cents=150, event_id="evt_rev_discount_1"
    )

    after = (await client.get("/admin/stats", headers=admin_headers)).json()["total_revenue_cents_30d"]
    assert after - before == 150


async def test_dashboard_stats_includes_dau_and_reported_fields(client):
    admin_id, admin_headers = await create_user_with_profile(client, "admin_dau@example.com")
    await _make_admin(admin_id)

    stats = (await client.get("/admin/stats", headers=admin_headers)).json()
    for key in ("active_today", "reported_users"):
        assert key in stats


async def test_demographics_gender_and_mbti_gender_split(client):
    admin_id, admin_headers = await create_user_with_profile(client, "admin_demo@example.com")
    await _make_admin(admin_id)

    await create_user_with_profile(
        client, "demo_f1@example.com", gender="female", interested_in="male", mbti="INTJ"
    )
    await create_user_with_profile(
        client, "demo_m1@example.com", gender="male", interested_in="female", mbti="INTJ"
    )

    resp = await client.get("/admin/demographics", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()

    gender_counts = {b["key"]: b["count"] for b in body["gender"]}
    assert gender_counts.get("female", 0) >= 1
    assert gender_counts.get("male", 0) >= 1

    intj = next(b for b in body["mbti"] if b["key"] == "INTJ")
    assert intj["female"] >= 1
    assert intj["male"] >= 1


async def test_demographics_height_buckets_group_into_5cm_ranges(client):
    admin_id, admin_headers = await create_user_with_profile(client, "admin_height@example.com")
    await _make_admin(admin_id)

    await create_user_with_profile(client, "height_a@example.com", gender="female", interested_in="male", height_cm=172)
    await create_user_with_profile(client, "height_b@example.com", gender="female", interested_in="male", height_cm=174)

    resp = await client.get("/admin/demographics", headers=admin_headers)
    body = resp.json()
    bucket = next((b for b in body["height_cm"] if b["key"] == "170-174"), None)
    assert bucket is not None
    assert bucket["count"] >= 2


async def test_signups_timeseries_returns_points_and_pct_change(client):
    admin_id, admin_headers = await create_user_with_profile(client, "admin_ts@example.com")
    await _make_admin(admin_id)

    resp = await client.get("/admin/timeseries", headers=admin_headers, params={"metric": "signups", "period": "1w"})
    assert resp.status_code == 200
    body = resp.json()
    assert "points" in body
    assert "total_in_period" in body
    assert "pct_change" in body


async def test_signups_timeseries_all_period_has_no_pct_change(client):
    admin_id, admin_headers = await create_user_with_profile(client, "admin_ts_all@example.com")
    await _make_admin(admin_id)

    resp = await client.get("/admin/timeseries", headers=admin_headers, params={"metric": "signups", "period": "all"})
    assert resp.status_code == 200
    assert resp.json()["pct_change"] is None


async def test_timeseries_rejects_unknown_metric(client):
    admin_id, admin_headers = await create_user_with_profile(client, "admin_ts_bad@example.com")
    await _make_admin(admin_id)

    resp = await client.get("/admin/timeseries", headers=admin_headers, params={"metric": "bogus"})
    assert resp.status_code == 422
