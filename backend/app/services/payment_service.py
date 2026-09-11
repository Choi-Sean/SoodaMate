import json
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.iap import PaymentTransaction
from app.models.profile import Profile
from app.utils.premium import is_premium
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
    # Blind chat monetization (see services/blind_chat_service.py). AI match
    # credits are consumable, same shape as superlike/boost above.
    "ai_match_pack_1": {
        "name": "AI 매칭권 1회",
        "credit_kind": "ai_match",
        "credits": 1,
        "price_usd_cents": 199,
    },
    "ai_match_pack_5": {
        "name": "AI 매칭권 5회",
        "credit_kind": "ai_match",
        "credits": 5,
        "price_usd_cents": 699,
    },
    # unlimited_matching_days is a fixed-duration top-up (extends
    # Profile.unlimited_matching_until), not a real Stripe Subscription like
    # membership_* below — nothing to cancel, only more time to stack on top
    # of whatever's left (same one-time-purchase mode as superlike/boost).
    "unlimited_matching_week": {
        "name": "무제한 매칭 1주일",
        "credit_kind": "unlimited_matching_days",
        "days": 7,
        "price_usd_cents": 399,
    },
    "unlimited_matching_month": {
        "name": "무제한 매칭 1개월",
        "credit_kind": "unlimited_matching_days",
        "days": 30,
        "price_usd_cents": 699,
    },
    # Real recurring Stripe Subscriptions (mode="subscription" below), not
    # one-time top-ups — create_checkout_session/handle_webhook_event branch
    # on credit_kind == "membership" to use the subscription path.
    "membership_monthly": {
        "name": "프리미엄 멤버십 (월간)",
        "credit_kind": "membership",
        "billing_cycle": "monthly",
        "interval": "month",
        "price_usd_cents": 999,
    },
    "membership_yearly": {
        "name": "프리미엄 멤버십 (연간)",
        "credit_kind": "membership",
        "billing_cycle": "yearly",
        "interval": "year",
        # ~2 months free vs. paying monthly — the usual yearly-plan discount.
        "price_usd_cents": 9999,
    },
}

# Stripe Checkout's product_data.name is the only product label the buyer
# actually sees (it's rendered on Stripe's own hosted checkout page, outside
# our site entirely) - PRODUCTS[...]["name"] above stays a single Korean
# label for internal/dashboard purposes, but the checkout page itself should
# match whatever language the buyer uses the app in. Mirrors the same
# strings shop.html shows via web/i18n.js's shop.product.<id>.name keys -
# keep both in sync if a product's copy changes. Falls back to English for
# an unsupported/unset preferred_language, same convention as
# push_i18n.py's SUPPORTED_PUSH_LANGUAGES fallback.
_PRODUCT_NAMES: dict[str, dict[str, str]] = {
    "superlike_pack_5": {
        "ko": "슈퍼좋아요 5개", "en": "Super Like x5", "es": "5 Super Likes",
        "zh": "超级喜欢 x5", "ja": "スーパーいいね ×5",
    },
    "superlike_pack_20": {
        "ko": "슈퍼좋아요 20개", "en": "Super Like x20", "es": "20 Super Likes",
        "zh": "超级喜欢 x20", "ja": "スーパーいいね ×20",
    },
    "boost_1": {
        "ko": "부스트 1회", "en": "Boost x1", "es": "1 Boost",
        "zh": "曝光加速 x1", "ja": "ブースト ×1",
    },
    "ai_match_pack_1": {
        "ko": "AI 매칭권 1회", "en": "AI Match x1", "es": "1 Match con IA",
        "zh": "AI匹配 x1", "ja": "AIマッチ ×1",
    },
    "ai_match_pack_5": {
        "ko": "AI 매칭권 5회", "en": "AI Match x5", "es": "5 Matches con IA",
        "zh": "AI匹配 x5", "ja": "AIマッチ ×5",
    },
    "unlimited_matching_week": {
        "ko": "무제한 매칭 1주일", "en": "Unlimited Matching — 1 week", "es": "Matching ilimitado — 1 semana",
        "zh": "无限匹配 — 1周", "ja": "無制限マッチング — 1週間",
    },
    "unlimited_matching_month": {
        "ko": "무제한 매칭 1개월", "en": "Unlimited Matching — 1 month", "es": "Matching ilimitado — 1 mes",
        "zh": "无限匹配 — 1个月", "ja": "無制限マッチング — 1ヶ月",
    },
    "membership_monthly": {
        "ko": "프리미엄 멤버십", "en": "Premium Membership", "es": "Membresía Premium",
        "zh": "高级会员", "ja": "プレミアム会員",
    },
    "membership_yearly": {
        "ko": "프리미엄 멤버십", "en": "Premium Membership", "es": "Membresía Premium",
        "zh": "高级会员", "ja": "プレミアム会員",
    },
}


def _localized_product_name(product_id: str, product: dict, language: str) -> str:
    names = _PRODUCT_NAMES.get(product_id)
    if not names:
        return product["name"]
    return names.get(language) or names["en"]


# All of this app's products are digital features of the app itself
# (subscription access or in-app credits), delivered over the internet with
# nothing downloaded and no business use - Stripe Tax (required now that
# Managed Payments is enabled on the account) needs a product tax code on
# every line item to classify it; without one, Checkout Session creation
# fails outright with "the product tax code is missing" before a buyer ever
# sees a payment form. See https://docs.stripe.com/tax/tax-categories.
_SAAS_PERSONAL_USE_TAX_CODE = "txcd_10103000"

BOOST_DURATION_MINUTES = 30
# checkout.session.completed only fires once, at subscription creation — a
# real renewal charge is a separate invoice.payment_succeeded event this app
# doesn't handle (no live Stripe test account to exercise it against this
# session), so premium_until is approximated as now + one billing period
# rather than read from Stripe's own current_period_end.
CYCLE_DAYS = {"monthly": 30, "yearly": 365}


def _get_stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "payments are not configured yet")
    stripe.api_key = settings.stripe_secret_key
    return stripe


def list_products() -> list[dict]:
    return [{"product_id": pid, **info} for pid, info in PRODUCTS.items()]


async def create_checkout_session(user_id: uuid.UUID, product_id: str, language: str = "en") -> str:
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown product_id")

    is_subscription = product["credit_kind"] == "membership"
    price_data: dict = {
        "currency": "usd",
        "unit_amount": product["price_usd_cents"],
        "product_data": {
            "name": _localized_product_name(product_id, product, language),
            "tax_code": _SAAS_PERSONAL_USE_TAX_CODE,
        },
    }
    if is_subscription:
        price_data["recurring"] = {"interval": product["interval"]}

    stripe_client = _get_stripe()
    session = stripe_client.checkout.Session.create(
        mode="subscription" if is_subscription else "payment",
        client_reference_id=str(user_id),
        metadata={"user_id": str(user_id), "product_id": product_id},
        line_items=[{"price_data": price_data, "quantity": 1}],
        success_url=f"{settings.web_base_url}/shop-success.html?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.web_base_url}/shop.html",
    )
    return session.url


async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str | None) -> None:
    stripe_client = _get_stripe()
    try:
        stripe_client.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid webhook signature") from exc

    # construct_event returns a stripe.Event whose nested `data.object` is a
    # typed StripeObject (a Session, etc.) that no longer supports dict
    # methods like .get() in stripe-python >= 12 — it raises AttributeError
    # instead. The raw payload is already signature-verified above, so parse
    # it straight to a plain dict and work with that.
    event = json.loads(payload)

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
        # Membership products don't have a "credits" count (they grant a
        # subscription, not a consumable balance) - 0 rather than None
        # since CreditsGranted is NOT NULL.
        credits_granted=product.get("credits") or 0,
        raw_payload=payload.decode("utf-8", "replace"),
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
    elif product["credit_kind"] == "ai_match":
        profile.ai_match_credits += product["credits"]
    elif product["credit_kind"] == "unlimited_matching_days":
        # Stacks on top of remaining time, same as superlike/boost credits —
        # unlike membership below, this isn't a subscription that replaces
        # what was there.
        base = profile.unlimited_matching_until
        if base is not None and base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        start = max(base, datetime.now(timezone.utc)) if base else datetime.now(timezone.utc)
        profile.unlimited_matching_until = start + timedelta(days=product["days"])
    elif product["credit_kind"] == "membership":
        # A fresh subscription, not a top-up — no stacking on remaining
        # time (that made sense for the old one-time-purchase model, not a
        # recurring one), and the new billing_cycle/price/subscription-id
        # fully replace whatever was there before (e.g. a prior canceled
        # plan).
        profile.premium_until = datetime.now(timezone.utc) + timedelta(days=CYCLE_DAYS[product["billing_cycle"]])
        profile.billing_cycle = product["billing_cycle"]
        profile.subscription_price_cents = product["price_usd_cents"]
        profile.stripe_subscription_id = session_obj.get("subscription")
        profile.cancel_at_period_end = False
    await db.commit()


def is_premium_member(profile: Profile) -> bool:
    return is_premium(profile.premium_until)


async def cancel_subscription(db: AsyncSession, user_id: uuid.UUID) -> datetime:
    """Cancels at period end, not immediately — the user keeps premium
    through whatever they already paid for (see the no-refund policy shown
    alongside both checkout and this action); Stripe just won't charge them
    again after that."""
    profile = await db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "complete your profile first")
    if not profile.stripe_subscription_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no active subscription to cancel")
    if profile.cancel_at_period_end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "subscription is already set to cancel")

    stripe_client = _get_stripe()
    try:
        stripe_client.Subscription.modify(profile.stripe_subscription_id, cancel_at_period_end=True)
    except stripe.error.StripeError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "couldn't reach the payment provider") from exc

    profile.cancel_at_period_end = True
    await db.commit()
    return profile.premium_until


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
