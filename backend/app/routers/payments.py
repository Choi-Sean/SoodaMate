from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.payment import (
    BalanceResponse,
    BoostActivateResponse,
    CreateCheckoutRequest,
    CreateCheckoutResponse,
    ProductOut,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/products", response_model=list[ProductOut])
async def get_products() -> list[ProductOut]:
    return [ProductOut(**p) for p in payment_service.list_products()]


@router.post("/create-checkout-session", response_model=CreateCheckoutResponse)
async def create_checkout_session(
    body: CreateCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreateCheckoutResponse:
    checkout_url = await payment_service.create_checkout_session(user.id, body.product_id)
    return CreateCheckoutResponse(checkout_url=checkout_url)


@router.post("/webhook", status_code=204)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> None:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    await payment_service.handle_webhook_event(db, payload, sig_header)


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> BalanceResponse:
    profile = await db.get(Profile, user.id)
    return BalanceResponse(
        superlike_credits=profile.superlike_credits if profile else 0,
        boost_credits=profile.boost_credits if profile else 0,
        boost_active_until=profile.boost_active_until if profile else None,
    )


@router.post("/activate-boost", response_model=BoostActivateResponse)
async def activate_boost(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> BoostActivateResponse:
    active_until = await payment_service.activate_boost(db, user.id)
    return BoostActivateResponse(boost_active_until=active_until)
