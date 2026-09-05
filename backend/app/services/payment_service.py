import uuid
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.iap import PaymentTransaction
from app.models.profile import Profile
from app.utils.upsert import try_insert

# Product catalog lives in code, not Stripe Dashboard "Prices" — inline
# price_data on the Checkout Session means no pre-created Stripe product/price
# IDs are needed as an external prerequisite, only the Stripe secret key is.
PRODUCTS: dict[str, dict] = {
    "superlike_pack_5": {
        "name": "슈퍼좋아요 5개",
        "credit_kind": "superlike",
        "credits": 5,
        "price_usd_cents": 499,
    },
    "superlike_pack_20": {
        "name": "슈퍼좋아요 20개",
        "credit_kind": "superlike",
        "credits": 20,
        "price_usd_cents": 1499,
    },
    "boost_1": {
        "name": "부스트 1회",
        "credit_kind": "boost",
        "credits": 1,
        "price_usd_cents": 399,
    },
}

BOOST_DURATION_MINUTES = 30


def _get_stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "payments are not configured yet")
    stripe.api_key = settings.stripe_secret_key
    return stripe


def list_products() -> list[dict]:
    return [{"product_id": pid, **info} for pid, info in PRODUCTS.items()]


async def create_checkout_session(user_id: uuid.UUID, product_id: str) -> str:
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown product_id")

    stripe_client = _get_stripe()
    session = stripe_client.checkout.Session.create(
        mode="payment",
        client_reference_id=str(user_id),
        metadata={"user_id": str(user_id), "product_id": product_id},
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": product["price_usd_cents"],
                    "product_data": {"name": product["name"]},
                },
                "quantity": 1,
            }
        ],
        success_url=f"{settings.web_base_url}/shop-success.html?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.web_base_url}/shop.html",
    )
    return session.url


async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str | None) -> None:
    stripe_client = _get_stripe()
    try:
        event = stripe_client.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid webhook signature") from exc

    if event["type"] != "checkout.session.completed":
        return  # not a purchase event we act on (e.g. subscription renewals — not used here)

    session_obj = event["data"]["object"]
    metadata = session_obj.get("metadata") or {}
    user_id_str = metadata.get("user_id")
    product_id = metadata.get("product_id")
    if not user_id_str or product_id not in PRODUCTS:
        return

    product = PRODUCTS[product_id]
    transaction = PaymentTransaction(
        user_id=uuid.UUID(user_id_str),
        stripe_event_id=event["id"],
        stripe_session_id=session_obj["id"],
        product_id=product_id,
        credit_kind=product["credit_kind"],
        credits_granted=product["credits"],
        raw_payload=str(event),
    )
    inserted = await try_insert(db, transaction)
    if not inserted:
        return  # webhook redelivery of an event we already processed — no-op, never double-grant

    profile = await db.get(Profile, uuid.UUID(user_id_str))
    if profile is None:
        await db.commit()
        return
    if product["credit_kind"] == "superlike":
        profile.superlike_credits += product["credits"]
    elif product["credit_kind"] == "boost":
        profile.boost_credits += product["credits"]
    await db.commit()


async def activate_boost(db: AsyncSession, user_id: uuid.UUID) -> datetime:
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    if profile.boost_credits <= 0:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "no boost credits left")

    profile.boost_credits -= 1
    # Purchase and activation are separate steps on purpose — a 3am purchase
    # shouldn't silently start burning the visibility window unattended.
    profile.boost_active_until = datetime.now(timezone.utc) + timedelta(minutes=BOOST_DURATION_MINUTES)
    await db.commit()
    return profile.boost_active_until
