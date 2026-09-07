from datetime import datetime

from pydantic import BaseModel


class ProductOut(BaseModel):
    product_id: str
    name: str
    credit_kind: str
    # Consumable products (superlike/boost packs) set credits; membership
    # products are a recurring subscription instead and set billing_cycle -
    # each kind only ever populates the field that applies to it.
    credits: int | None = None
    billing_cycle: str | None = None
    price_usd_cents: int


class CreateCheckoutRequest(BaseModel):
    product_id: str


class CreateCheckoutResponse(BaseModel):
    checkout_url: str


class BoostActivateResponse(BaseModel):
    boost_active_until: datetime


class BalanceResponse(BaseModel):
    superlike_credits: int
    boost_credits: int
    boost_active_until: datetime | None
