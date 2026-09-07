import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid or expired token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not an access token")

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active or user.is_banned:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Gates the face-verification review endpoints (soodamate.com/verify).
    is_admin is never settable through the API — it's flipped directly in
    the DB for the app owner's own account."""
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin access required")
    return user
