from datetime import datetime

from pydantic import BaseModel


class ProductOut(BaseModel):
    product_id: str
    name: str
    credit_kind: str
    credits: int
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
