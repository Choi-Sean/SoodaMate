from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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


@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.signup_with_email(db, body.email, body.password)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.login_with_email(db, body.email, body.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await auth_service.refresh_access_token(db, body.refresh_token)


@router.post("/google", response_model=TokenResponse)
async def google_login(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        identity = await google_verifier.verify(body.id_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return await auth_service.login_or_signup_with_provider(db, "google", identity)


@router.post("/apple", response_model=TokenResponse)
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
@router.post("/phone/start", status_code=204)
async def start_phone_auth(body: PhoneAuthStartRequest) -> None:
    await auth_service.start_phone_auth(sms_verifier, body.phone_number)


@router.post("/phone/confirm", response_model=PhoneAuthResponse)
async def confirm_phone_auth(
    body: PhoneAuthConfirmRequest, db: AsyncSession = Depends(get_db)
) -> PhoneAuthResponse:
    tokens, is_new_user = await auth_service.login_or_signup_with_phone(
        db, sms_verifier, body.phone_number, body.code
    )
    return PhoneAuthResponse(**tokens.model_dump(), is_new_user=is_new_user)
