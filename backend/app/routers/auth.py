from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import rate_limit
from app.core.phone import normalize_e164
from app.database import get_db
from app.schemas.auth import (
    AppleAuthRequest,
    GoogleAuthRequest,
    LoginRequest,
    PhoneAuthConfirmRequest,
    PhoneAuthResponse,
    PhoneAuthStartRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
)
from app.services import auth_service
from app.services.oauth.apple import apple_verifier
from app.services.oauth.google import google_verifier
from app.services.sms.twilio_verify import sms_verifier

router = APIRouter(prefix="/auth", tags=["auth"])


async def require_legacy_auth() -> None:
    """Email sign-up and Google/Apple sign-in are switched off (settings.
    enable_legacy_auth): the app only offers phone sign-in, and these paths let
    anyone mint accounts that skipped phone verification and the VoIP screen.
    404 rather than 403 — as far as a caller can tell the endpoint isn't there."""
    if not settings.enable_legacy_auth:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not found")


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=201,
    dependencies=[Depends(require_legacy_auth), Depends(rate_limit.limit_ip("signup", 10, 3600))],
)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.signup_with_email(db, body.email, body.password)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit.limit_ip("login", 200, 600))])
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    # Keyed by the account being attacked, not the caller: a botnet rotating IPs
    # is still capped at 10 guesses per 10 minutes per email.
    rate_limit.enforce("login:email", body.email.strip().lower(), 10, 600)
    return await auth_service.login_with_email(db, body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.refresh_access_token(db, body.refresh_token)


@router.post("/google", response_model=TokenResponse, dependencies=[Depends(require_legacy_auth)])
async def google_login(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        identity = await google_verifier.verify(body.id_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await auth_service.login_or_signup_with_provider(db, "google", identity)


@router.post("/apple", response_model=TokenResponse, dependencies=[Depends(require_legacy_auth)])
async def apple_login(body: AppleAuthRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        identity = await apple_verifier.verify(body.identity_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await auth_service.login_or_signup_with_provider(db, "apple", identity)


# Phone is now the app's primary (only, in the mobile UI) sign-in method —
# PhoneAuthScreen calls these two directly, with no prior JWT. Distinct from
# /verification/phone/* (app/routers/verification.py), which attaches a
# phone number to an *already-logged-in* account instead of authenticating.
@router.post(
    "/phone/start", status_code=204, dependencies=[Depends(rate_limit.limit_ip("phone_start", 300, 3600))]
)
async def start_phone_auth(body: PhoneAuthStartRequest, db: AsyncSession = Depends(get_db)) -> None:
    # Every start can cost a billed SMS (plus a Lookup): cap it per number, and
    # globally so SMS-pumping can't scale by rotating numbers and IPs.
    phone = normalize_e164(body.phone_number)
    rate_limit.enforce("phone_start:number", phone, 5, 600)
    rate_limit.enforce("phone_start:global", "all", settings.sms_global_per_10min, 600)
    await auth_service.start_phone_auth(db, sms_verifier, body.phone_number)


@router.post(
    "/phone/confirm",
    response_model=PhoneAuthResponse,
    dependencies=[Depends(rate_limit.limit_ip("phone_confirm", 400, 600))],
)
async def confirm_phone_auth(
    body: PhoneAuthConfirmRequest, db: AsyncSession = Depends(get_db)
) -> PhoneAuthResponse:
    # 6-digit codes: without a ceiling here a determined caller could simply
    # try them all (the SMS provider's own attempt limit is only a second line).
    rate_limit.enforce("phone_confirm:number", normalize_e164(body.phone_number), 10, 600)
    tokens, is_new_user = await auth_service.login_or_signup_with_phone(
        db, sms_verifier, body.phone_number, body.code
    )
    return PhoneAuthResponse(**tokens.model_dump(), is_new_user=is_new_user)
