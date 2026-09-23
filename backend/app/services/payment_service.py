import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

import stripe
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.user_lock import user_lock
from app.models.iap import PaymentTransaction
from app.models.profile import Profile
from app.models.promotion import Promotion
from app.schemas.payment import PurchaseHistoryItemOut
from app.utils.premium import is_premium
from app.utils.upsert import try_insert

# Product catalog lives in code, not Stripe Dashboard "Prices" — inline
# price_data on the Checkout Session means no pre-created Stripe product/price
# IDs are needed as an external prerequisite, only the Stripe secret key is.
#
# Ordered blind-chat-first (Blind Chat is the app's primary flow — see
# soodamate-blind-chat-apple-policy-risk memory) since dict insertion order
# is what list_products() renders, top to bottom. Classic Matching's
# superlike/boost entries are marked "listed": False (see list_products())
# rather than deleted — MyProfileScreen's Classic Matching link card was
# hidden per product decision (swipe-based matching doesn't fit the Blind
# Chat concept), so these products have no in-app screen left to use them
# on; kept in the catalog (not removed) so nothing breaks for anyone who
# already bought credits, and so this is a one-line revert if that decision
# changes.
PRODUCTS: dict[str, dict] = {
    # Blind chat monetization (see services/blind_chat_service.py). AI match
    # credits are consumable, same shape as superlike/boost below.
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
    # Gender-neutral, unlike the Bumble-style first-message/first-call rules —
    # anyone can buy and use it. Consumed by POST /matches/{id}/blind-peek
    # (services/match_service.use_blind_peek): lets the buyer alone see the
    # other side's real profile in a still-anonymous blind match, without the
    # other side ever finding out. See soodamate-blind-chat-open-decisions-
    # style product note: this one-sidedly breaks Blind Chat's "mutual
    # consent to reveal" promise, so the same disclosure was added to
    # terms.html (Article 6).
    "blind_peek_1": {
        "name": "몰래보기권 1회",
        "credit_kind": "blind_peek",
        "credits": 1,
        "price_usd_cents": 299,
    },
    # Real recurring Stripe Subscriptions (mode="subscription" below), not
    # one-time top-ups — create_checkout_session/handle_webhook_event branch
    # on credit_kind == "membership" to use the subscription path. Also
    # grants unlimited blind-chat matching for free (see
    # blind_chat_service.is_unlimited_matching_active), on top of the
    # Classic Matching perks below.
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
    # Classic Matching (swipe-based Discover) monetization — hidden from the
    # shop (see list_products()) since the only screen that used these
    # credits is no longer linked from anywhere in the app.
    "superlike_pack_5": {
        "name": "슈퍼좋아요 5개",
        "credit_kind": "superlike",
        "credits": 5,
        "price_usd_cents": 499,
        "listed": False,
    },
    "superlike_pack_20": {
        "name": "슈퍼좋아요 20개",
        "credit_kind": "superlike",
        "credits": 20,
        "price_usd_cents": 1499,
        "listed": False,
    },
    "boost_1": {
        "name": "부스트 1회",
        "credit_kind": "boost",
        "credits": 1,
        "price_usd_cents": 399,
        "listed": False,
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
    "blind_peek_1": {
        "ko": "몰래보기권 1회", "en": "Secret Peek x1", "es": "1 Vistazo secreto",
        "zh": "偷看卡 x1", "ja": "こっそり閲覧 ×1",
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

logger = logging.getLogger(__name__)

BOOST_DURATION_MINUTES = 30
# checkout.session.completed only fires once, at subscription creation; renewals arrive
# as invoice.paid events (handled in _handle_subscription_invoice_paid), which set
# premium_until from the invoice's real period end. At creation time premium_until is
# approximated as now + one billing period.
CYCLE_DAYS = {"monthly": 30, "yearly": 365}


def _get_stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "payments are not configured yet")
    stripe.api_key = settings.stripe_secret_key
    return stripe


async def get_active_discounts(db: AsyncSession) -> dict[str, int]:
    """{product_id: discount_percent} for every currently-active Promotion
    (routers/admin.py) — at most one active row per product_id in practice
    (enforced when a promotion is created), but this takes the newest if
    that's ever violated."""
    rows = (
        await db.execute(
            select(Promotion.product_id, Promotion.discount_percent)
            .where(Promotion.is_active)
            .order_by(Promotion.created_at.desc())
        )
    ).all()
    discounts: dict[str, int] = {}
    for product_id, discount_percent in rows:
        discounts.setdefault(product_id, discount_percent)
    return discounts


def _discounted_cents(price_usd_cents: int, discount_percent: int | None) -> int:
    if not discount_percent:
        return price_usd_cents
    return round(price_usd_cents * (100 - discount_percent) / 100)


def list_products(discounts: dict[str, int] | None = None) -> list[dict]:
    # "listed": False products (see PRODUCTS' Classic Matching entries)
    # stay fully purchasable via create_checkout_session/the webhook — only
    # hidden from what the shop actually shows.
    discounts = discounts or {}
    out = []
    for pid, info in PRODUCTS.items():
        if not info.get("listed", True):
            continue
        discount_percent = discounts.get(pid)
        out.append(
            {
                "product_id": pid,
                **info,
                "discount_percent": discount_percent,
                "discounted_price_usd_cents": _discounted_cents(info["price_usd_cents"], discount_percent)
                if discount_percent
                else None,
            }
        )
    return out


async def create_checkout_session(
    db: AsyncSession, user_id: uuid.UUID, product_id: str, language: str = "en"
) -> str:
    product = PRODUCTS.get(product_id)
    if product is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown product_id")

    if product["credit_kind"] == "membership":
        # A second subscription for the same plan would just bill the customer
        # twice for one benefit (double-tap on Buy, or buying again from a stale
        # page). Switching to the other billing cycle is still allowed — the
        # webhook cancels the superseded subscription so it can't keep billing.
        profile = await db.get(Profile, user_id)
        if (
            profile is not None
            and profile.stripe_subscription_id
            and not profile.cancel_at_period_end
            and is_premium(profile.premium_until)
            and profile.billing_cycle == product["billing_cycle"]
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "you already have an active membership")

    discounts = await get_active_discounts(db)
    unit_amount = _discounted_cents(product["price_usd_cents"], discounts.get(product_id))

    is_subscription = product["credit_kind"] == "membership"
    price_data: dict = {
        "currency": "usd",
        "unit_amount": unit_amount,
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
    if not settings.stripe_webhook_secret:
        # With no signing secret configured a signature can be forged with an
        # empty key, so an unconfigured endpoint must refuse everything rather
        # than "verify" against nothing.
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "webhook is not configured")
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

    # A membership is a recurring Stripe subscription: checkout.session.completed
    # only fires for the FIRST charge. Every later billing cycle arrives as an
    # invoice event, and without handling it Stripe keeps charging the customer
    # while premium quietly lapses after one period. (Requires these events to be
    # enabled on the webhook endpoint in the Stripe dashboard.)
    if event["type"] in ("invoice.paid", "invoice.payment_succeeded"):
        await _handle_subscription_invoice_paid(db, event, payload)
        return
    if event["type"] == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, event)
        return
    if event["type"] != "checkout.session.completed":
        return  # not an event we act on

    session_obj = event["data"]["object"]
    metadata = session_obj.get("metadata") or {}
    user_id_str = metadata.get("user_id")
    product_id = metadata.get("product_id")
    if not user_id_str or product_id not in PRODUCTS:
        return

    try:
        purchaser_id = uuid.UUID(str(user_id_str))
    except ValueError:
        return  # malformed metadata: acknowledge (200) so Stripe doesn't retry forever, grant nothing

    product = PRODUCTS[product_id]
    transaction = PaymentTransaction(
        user_id=purchaser_id,
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

    superseded_subscription: str | None = None
    # Grants and spends of the same user's credits are serialized (see
    # core/user_lock.py) so a webhook can't interleave with a spend and lose an update.
    async with user_lock(f"credits:{purchaser_id}"):
        profile = await db.get(Profile, purchaser_id)
        if profile is None:
            await db.commit()
            return
        if product["credit_kind"] == "superlike":
            profile.superlike_credits += product["credits"]
        elif product["credit_kind"] == "boost":
            profile.boost_credits += product["credits"]
        elif product["credit_kind"] == "ai_match":
            profile.ai_match_credits += product["credits"]
        elif product["credit_kind"] == "blind_peek":
            profile.stealth_peek_credits += product["credits"]
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
            superseded_subscription = profile.stripe_subscription_id
            profile.premium_until = datetime.now(timezone.utc) + timedelta(days=CYCLE_DAYS[product["billing_cycle"]])
            profile.billing_cycle = product["billing_cycle"]
            profile.subscription_price_cents = product["price_usd_cents"]
            profile.stripe_subscription_id = session_obj.get("subscription")
            profile.cancel_at_period_end = False
        await db.commit()

    new_subscription = session_obj.get("subscription")
    if superseded_subscription and new_subscription and superseded_subscription != new_subscription:
        # The customer switched plans: the previous subscription would otherwise
        # keep billing forever, out of reach of the in-app cancel button (which
        # only knows the latest subscription id).
        try:
            stripe_client.Subscription.cancel(superseded_subscription)
        except Exception:  # noqa: BLE001 - never fail the webhook over this; it is logged for follow-up
            logger.exception("could not cancel superseded subscription %s", superseded_subscription)


def _invoice_subscription_id(invoice: dict) -> str | None:
    """The subscription an invoice belongs to — top-level `subscription` on older
    Stripe API versions, `parent.subscription_details.subscription` on newer ones."""
    sub = invoice.get("subscription")
    if isinstance(sub, dict):
        sub = sub.get("id")
    if not sub:
        sub = ((invoice.get("parent") or {}).get("subscription_details") or {}).get("subscription")
    return sub if isinstance(sub, str) and sub else None


def _invoice_period_end(invoice: dict) -> datetime | None:
    ends = []
    for line in (invoice.get("lines") or {}).get("data", []) or []:
        end = (line.get("period") or {}).get("end") if isinstance(line, dict) else None
        if isinstance(end, (int, float)):
            ends.append(end)
    return datetime.fromtimestamp(max(ends), tz=timezone.utc) if ends else None


async def _handle_subscription_invoice_paid(db: AsyncSession, event: dict, payload: bytes) -> None:
    invoice = event["data"]["object"]
    subscription_id = _invoice_subscription_id(invoice)
    period_end = _invoice_period_end(invoice)
    if not subscription_id or period_end is None:
        return
    profile = await db.scalar(select(Profile).where(Profile.stripe_subscription_id == subscription_id))
    if profile is None:
        # The very first invoice can arrive before checkout.session.completed has
        # stored the subscription id; that handler covers the first period.
        return
    purchaser_id = profile.user_id
    cycle_product = f"membership_{profile.billing_cycle}"
    transaction = PaymentTransaction(
        user_id=purchaser_id,
        stripe_event_id=event["id"],
        stripe_session_id=str(invoice.get("id") or "invoice"),
        product_id=cycle_product if cycle_product in PRODUCTS else "membership_monthly",
        credit_kind="membership",
        credits_granted=0,
        raw_payload=payload.decode("utf-8", "replace"),
    )
    if not await try_insert(db, transaction):
        return  # redelivery of an event we already processed
    async with user_lock(f"credits:{purchaser_id}"):
        current = await db.get(Profile, purchaser_id)
        if current is None:
            await db.commit()
            return
        existing = current.premium_until
        if existing is not None and existing.tzinfo is None:
            existing = existing.replace(tzinfo=timezone.utc)
        if existing is None or period_end > existing:
            current.premium_until = period_end
        await db.commit()


async def _handle_subscription_deleted(db: AsyncSession, event: dict) -> None:
    subscription_id = (event["data"]["object"] or {}).get("id")
    if not isinstance(subscription_id, str) or not subscription_id:
        return
    profile = await db.scalar(select(Profile).where(Profile.stripe_subscription_id == subscription_id))
    if profile is None:
        return
    # Ended (canceled at period end, or Stripe gave up after failed payments).
    # premium_until is left alone: whatever was paid for stays valid until then,
    # but the stale id must go or the in-app cancel button would try to modify a
    # subscription that no longer exists.
    profile.stripe_subscription_id = None
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


async def get_purchase_history(
    db: AsyncSession, user_id: uuid.UUID, language: str
) -> list[PurchaseHistoryItemOut]:
    """Newest-first list of completed purchases — the user-facing answer to
    "did my payment actually go through", independent of whatever the
    profile's current balance happens to be (credits get spent, this
    doesn't). product_id no longer in PRODUCTS (a retired/renamed catalog
    entry) falls back to the raw id rather than 500ing."""
    rows = (
        await db.scalars(
            select(PaymentTransaction)
            .where(PaymentTransaction.user_id == user_id)
            .order_by(PaymentTransaction.created_at.desc())
        )
    ).all()
    items = []
    for row in rows:
        product = PRODUCTS.get(row.product_id)
        name = row.product_id
        if product:
            name = _localized_product_name(row.product_id, product, language)
        items.append(
            PurchaseHistoryItemOut(
                product_id=row.product_id,
                name=name,
                credit_kind=row.credit_kind,
                credits_granted=row.credits_granted,
                created_at=row.created_at,
            )
        )
    return items
