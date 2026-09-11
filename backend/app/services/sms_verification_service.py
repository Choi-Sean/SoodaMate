import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sms_verifier_base import SmsVerifier
from app.models.user import User

# E.164: '+' then 8-15 digits. The client is responsible for turning a
# local-format number into this via a country picker — this is just a sanity
# gate before we hand it to Twilio, not a full validation.
E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def _normalize(phone_number: str) -> str:
    if not E164_PATTERN.match(phone_number):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "phone_number must be in E.164 format, e.g. +821012345678")
    return phone_number


async def start_phone_verification(
    db: AsyncSession, verifier: SmsVerifier, user_id: uuid.UUID, phone_number: str
) -> None:
    phone_number = _normalize(phone_number)

    taken = await db.scalar(
        select(User).where(
            User.phone_number == phone_number,
            User.phone_verified_at.is_not(None),
            User.id != user_id,
        )
    )
    if taken is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "this phone number is already verified on another account")

    await verifier.start(phone_number)


async def confirm_phone_verification(
    db: AsyncSession, verifier: SmsVerifier, user_id: uuid.UUID, phone_number: str, code: str
) -> None:
    phone_number = _normalize(phone_number)

    approved = await verifier.check(phone_number, code)
    if not approved:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "incorrect or expired code")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

    user.phone_number = phone_number
    user.phone_verified_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError as exc:
        # Race: two accounts confirming the same number concurrently — the
        # pre-check above is best-effort, this filtered unique index is the
        # real guarantee.
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "this phone number is already verified on another account") from exc
