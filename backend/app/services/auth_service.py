import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth_provider_base import ExternalIdentity
from app.core.phone import normalize_e164
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.core.sms_verifier_base import SmsVerifier
from app.models.user import AuthProvider, User
from app.schemas.auth import TokenResponse
from app.services import phone_screening


def _is_dev_bypass_number(phone_number: str) -> bool:
    """Gate for the whitelisted-number/fixed-code shortcut below. Requires a
    non-empty dev_phone_bypass_code, so this is a no-op (matches nothing) in
    every environment except one where that's been deliberately set."""
    if not settings.dev_phone_bypass_code:
        return False
    return phone_number in settings.dev_phone_bypass_number_list


def issue_tokens(user_id: uuid.UUID) -> TokenResponse:
    return TokenResponse(
        access_token=create_token(user_id, "access"),
        refresh_token=create_token(user_id, "refresh"),
        user_id=user_id,
    )


async def signup_with_email(db: AsyncSession, email: str, password: str) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        # Tell the client *which* provider(s) this email is already linked
        # to (e.g. signed up via Google first) so it can show "log in with
        # Google" instead of a generic "already registered" dead end.
        linked = (
            await db.execute(select(AuthProvider.provider).where(AuthProvider.user_id == existing.id))
        ).scalars().all()
        oauth_providers = [p for p in linked if p != "email"]
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {"message": "email already registered", "providers": oauth_providers or ["email"]},
        )

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    await db.flush()
    db.add(AuthProvider(user_id=user.id, provider="email", provider_user_id=None))
    await db.commit()

    return issue_tokens(user.id)


async def login_with_email(db: AsyncSession, email: str, password: str) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid email or password")
    if user.is_banned or not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")

    return issue_tokens(user.id)


async def login_or_signup_with_provider(
    db: AsyncSession, provider: str, identity: ExternalIdentity
) -> TokenResponse:
    """Shared resolution path for Google/Apple/any future OAuth provider:
    find an existing linked account, or create a new user + link, then issue
    the same app-level JWT every auth path returns."""
    link = await db.scalar(
        select(AuthProvider).where(
            AuthProvider.provider == provider,
            AuthProvider.provider_user_id == identity.provider_user_id,
        )
    )
    if link is not None:
        user = await db.get(User, link.user_id)
        if user is None:
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "orphaned auth link")
        if user.is_banned or not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")
        return issue_tokens(user.id)

    # New identity. Only merge into an existing account when BOTH sides of the
    # match are trustworthy: the provider vouches for the email
    # (identity.email_verified) AND that account's email itself came from a
    # verified provider (it already has a Google/Apple link). An email that was
    # merely typed into PUT /account/email (or an email sign-up) proves nothing,
    # and merging on it would let anyone squat a victim's address and later
    # receive the victim's own Google/Apple sign-in into their account.
    user = None
    email_in_use = False
    if identity.email:
        existing = await db.scalar(select(User).where(User.email == identity.email))
        if existing is not None:
            email_in_use = True
            vouched = await db.scalar(
                select(AuthProvider.provider).where(
                    AuthProvider.user_id == existing.id, AuthProvider.provider.in_(("google", "apple"))
                ).limit(1)
            )
            if identity.email_verified and vouched is not None:
                user = existing

    if user is None:
        # users.email is unique: if the address is taken by an account we
        # refused to merge into, this one is created without an email.
        user = User(email=None if email_in_use else identity.email)
        db.add(user)
        await db.flush()

    db.add(AuthProvider(user_id=user.id, provider=provider, provider_user_id=identity.provider_user_id))
    await db.commit()

    return issue_tokens(user.id)


async def start_phone_auth(db: AsyncSession, verifier: SmsVerifier, phone_number: str) -> None:
    """Unauthenticated — unlike sms_verification_service.start_phone_verification
    (which attaches a phone to an already-logged-in account), this *is* the
    login/signup entry point. Twilio Verify's own per-number rate limiting is
    the abuse guard; on top of that, a number that isn't already a verified
    account must be a real mobile line (no VoIP/virtual) before we spend an
    SMS on it. Existing accounts skip that check so a later misclassification
    can never lock a returning user out."""
    phone_number = normalize_e164(phone_number)
    if _is_dev_bypass_number(phone_number):
        return

    existing_user_id = await db.scalar(
        select(User.id).where(User.phone_number == phone_number, User.phone_verified_at.is_not(None))
    )
    if existing_user_id is None:
        await phone_screening.assert_real_mobile_number(phone_number)
    await verifier.start(phone_number)


async def login_or_signup_with_phone(
    db: AsyncSession, verifier: SmsVerifier, phone_number: str, code: str
) -> tuple[TokenResponse, bool]:
    """Phone is the primary credential now (see PhoneAuthScreen) — confirming
    the code logs an existing account in or creates a new one, mirroring
    login_or_signup_with_provider's find-or-create shape for Google/Apple.
    Returns (tokens, is_new_user)."""
    phone_number = normalize_e164(phone_number)

    if _is_dev_bypass_number(phone_number) and code == settings.dev_phone_bypass_code:
        approved = True
    else:
        approved = await verifier.check(phone_number, code)
    if not approved:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "incorrect or expired code")

    user = await db.scalar(
        select(User).where(User.phone_number == phone_number, User.phone_verified_at.is_not(None))
    )
    if user is not None:
        if user.is_banned or not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")
        return issue_tokens(user.id), False

    user = User(phone_number=phone_number, phone_verified_at=datetime.now(timezone.utc))
    db.add(user)
    try:
        # The INSERT actually runs at flush, so the unique-index race
        # (double-tap / two devices confirming the same number at once) has
        # to be caught around the flush as well as the commit.
        await db.flush()
        db.add(AuthProvider(user_id=user.id, provider="phone", provider_user_id=None))
        await db.commit()
    except IntegrityError:
        # Race: two confirms for the same number landed concurrently (e.g. a
        # double-tap on "confirm"). The filtered unique index on
        # Users.PhoneNumber is the real guarantee — fall back to whichever
        # row actually won instead of erroring the second request out.
        await db.rollback()
        winner = await db.scalar(
            select(User).where(User.phone_number == phone_number, User.phone_verified_at.is_not(None))
        )
        if winner is None:
            raise
        return issue_tokens(winner.id), False

    return issue_tokens(user.id), True


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not a refresh token")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token") from exc
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.is_banned:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")

    return issue_tokens(user.id)
