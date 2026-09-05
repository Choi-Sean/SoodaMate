import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.email_sender_base import EmailSender
from app.core.security import hash_password, verify_password
from app.models.profile import Profile
from app.models.verification import Verification

CODE_EXPIRY_MINUTES = 15
MAX_ATTEMPTS = 5

# v1 heuristic for "is this a real work/school email": reject common personal
# providers. No curated allowlist of employer/school domains yet — expand
# later if false negatives (real work emails on a shared provider) turn out
# to matter in practice.
PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "naver.com",
    "daum.net",
    "hanmail.net",
    "kakao.com",
    "nate.com",
    "icloud.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "qq.com",
    "163.com",
}


def _domain_of(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


async def start_verification(
    db: AsyncSession, sender: EmailSender, user_id: uuid.UUID, kind: str, email: str
) -> None:
    if kind not in ("work", "school"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "kind must be 'work' or 'school'")

    domain = _domain_of(email)
    if domain in PERSONAL_EMAIL_DOMAINS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "use your work or school email address, not a personal one")

    code = f"{random.randint(0, 999999):06d}"
    existing = await db.scalar(
        select(Verification).where(Verification.user_id == user_id, Verification.kind == kind)
    )
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)

    if existing is not None:
        existing.email = email
        existing.domain = domain
        existing.code_hash = hash_password(code)
        existing.attempts = 0
        existing.expires_at = expires_at
        existing.verified_at = None
    else:
        db.add(
            Verification(
                user_id=user_id,
                kind=kind,
                email=email,
                domain=domain,
                code_hash=hash_password(code),
                expires_at=expires_at,
            )
        )

    # Unlike push_service's silent no-op-when-unconfigured pattern, a
    # verification code that never arrives is worse than an honest error —
    # this call raises (503, via SmtpEmailSender) if SMTP isn't configured,
    # and that propagates to the caller before we commit the new code.
    await sender.send(
        email,
        "수다메이트 인증 코드",
        f"인증 코드: {code}\n\n{CODE_EXPIRY_MINUTES}분 안에 입력해주세요.",
    )
    await db.commit()


async def confirm_verification(db: AsyncSession, user_id: uuid.UUID, kind: str, code: str) -> None:
    verification = await db.scalar(
        select(Verification).where(Verification.user_id == user_id, Verification.kind == kind)
    )
    if verification is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no verification in progress")

    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) >= expires_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "verification code expired")
    if verification.attempts >= MAX_ATTEMPTS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too many attempts")

    if not verify_password(code, verification.code_hash):
        verification.attempts += 1
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "incorrect code")

    verification.verified_at = datetime.now(timezone.utc)

    profile = await db.get(Profile, user_id)
    if profile is not None:
        profile.verified_badge = kind
    await db.commit()
