import uuid as uuid_mod
from datetime import datetime, timedelta, timezone

import pytest

from app.database import async_session_factory
from app.models.iap import PaymentTransaction
from tests.helpers import create_user_with_profile


@pytest.mark.asyncio
async def test_purchase_history_empty_for_new_user(client):
    _, headers = await create_user_with_profile(client, "historyEmpty@example.com")
    resp = await client.get("/payments/history", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"items": []}


@pytest.mark.asyncio
async def test_purchase_history_lists_transactions_newest_first_localized(client):
    user_id, headers = await create_user_with_profile(client, "historyItems@example.com")

    # Explicit, clearly-ordered created_at values rather than relying on
    # the column's own default — two rows inserted in the same commit can
    # otherwise land on the same DB timestamp (MSSQL DATETIME's ~3ms
    # rounding), making "newest first" order flaky/undefined between them.
    now = datetime.now(timezone.utc)
    async with async_session_factory() as session:
        session.add(
            PaymentTransaction(
                user_id=uuid_mod.UUID(user_id),
                stripe_event_id="evt_1",
                stripe_session_id="cs_1",
                product_id="ai_match_pack_5",
                credit_kind="ai_match",
                credits_granted=5,
                raw_payload="{}",
                created_at=now - timedelta(minutes=1),
            )
        )
        session.add(
            PaymentTransaction(
                user_id=uuid_mod.UUID(user_id),
                stripe_event_id="evt_2",
                stripe_session_id="cs_2",
                product_id="membership_monthly",
                credit_kind="membership",
                credits_granted=0,
                raw_payload="{}",
                created_at=now,
            )
        )
        await session.commit()

    resp = await client.get("/payments/history", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 2
    # Newest first (membership_monthly inserted second).
    assert items[0]["product_id"] == "membership_monthly"
    assert items[0]["name"] == "Premium Membership"  # default test-account language is "en"
    assert items[0]["credits_granted"] == 0
    assert items[1]["product_id"] == "ai_match_pack_5"
    assert items[1]["name"] == "AI Match x5"
    assert items[1]["credits_granted"] == 5
    # Internal-only fields never leak to the client.
    assert "stripe_event_id" not in items[0]
    assert "raw_payload" not in items[0]


@pytest.mark.asyncio
async def test_purchase_history_only_shows_the_requesting_users_own_rows(client):
    user_id, headers = await create_user_with_profile(client, "historyOwner@example.com")
    other_id, other_headers = await create_user_with_profile(client, "historyOther@example.com")

    async with async_session_factory() as session:
        session.add(
            PaymentTransaction(
                user_id=uuid_mod.UUID(other_id),
                stripe_event_id="evt_other",
                stripe_session_id="cs_other",
                product_id="ai_match_pack_1",
                credit_kind="ai_match",
                credits_granted=1,
                raw_payload="{}",
            )
        )
        await session.commit()

    resp = await client.get("/payments/history", headers=headers)
    assert resp.json() == {"items": []}

    resp_other = await client.get("/payments/history", headers=other_headers)
    assert len(resp_other.json()["items"]) == 1
