import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_provider_base import ExternalIdentity
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.user import AuthProvider, User
from app.schemas.auth import TokenResponse


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
    """Shared resolution path for Google/Kakao/any future OAuth provider:
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

    # New identity. If the provider gave us an email that already belongs to
    # an existing user, link this provider to that account instead of
    # creating a duplicate user.
    user = None
    if identity.email:
        user = await db.scalar(select(User).where(User.email == identity.email))

    if user is None:
        user = User(email=identity.email)
        db.add(user)
        await db.flush()

    db.add(AuthProvider(user_id=user.id, provider=provider, provider_user_id=identity.provider_user_id))
    await db.commit()

    return issue_tokens(user.id)


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    try:
        payload = decode_token(refresh_token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token") from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not a refresh token")

    user_id = uuid.UUID(payload["sub"])
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.is_banned:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")

    return issue_tokens(user.id)
