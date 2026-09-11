from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.couple_story import CoupleStoryReport
from app.models.interaction import Block, Match, Report, Swipe
from app.models.user import User
from app.services import payment_service

router = APIRouter(prefix="/account", tags=["account"])


class CancelSubscriptionOut(BaseModel):
    premium_until: datetime


class MeOut(BaseModel):
    id: str
    email: str | None
    phone_verified: bool
    preferred_language: str


@router.get("/me", response_model=MeOut)
async def get_me(user: User = Depends(get_current_user)) -> MeOut:
    # Deliberately independent of whether a Profile row exists yet (unlike
    # GET /profiles/me, which 404s pre-signup-completion) — RootNavigator
    # calls this first to decide the phone-verification gate, which now sits
    # *before* ProfileSetupScreen in the signup flow.
    return MeOut(
        id=str(user.id),
        email=user.email,
        phone_verified=user.phone_verified,
        preferred_language=user.preferred_language,
    )


class LanguageUpdateRequest(BaseModel):
    # Mirrors mobile/src/i18n's SUPPORTED_LANGUAGES.
    language: str = Field(pattern="^(ko|en|es|zh|ja)$")


@router.put("/language", status_code=204)
async def update_language(
    body: LanguageUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    # Kept in sync purely so push_service can send FCM notification text in
    # the language the user actually reads the app in — this has no effect
    # on in-app text, which the client's own i18next already handles.
    user.preferred_language = body.language
    await db.commit()


@router.post("/subscription/cancel", response_model=CancelSubscriptionOut)
async def cancel_subscription(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CancelSubscriptionOut:
    premium_until = await payment_service.cancel_subscription(db, user.id)
    return CancelSubscriptionOut(premium_until=premium_until)


@router.delete("/me", status_code=204)
async def delete_my_account(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    # Swipe/Match/Block/Report/CoupleStoryReport have no ondelete=CASCADE back
    # to users (MSSQL rejects two CASCADE paths to the same table from one
    # row) — deleted explicitly here, in this order, before the user row.
    # Matches must go before the user delete since Match.restricted_to_user_id
    # also points at users; deleting matches first also cascades to
    # messages/call_sessions/couple_stories (those DO still cascade from
    # matches.id, a single unambiguous path each). CoupleStoryReport.reporter_id
    # isn't reachable via that cascade (a report can target someone else's
    # story, on a match this user was never part of), so it's cleaned up
    # explicitly too. Everything else (profiles, photos, auth_providers,
    # push_tokens, verifications, iap_transactions) still cascades from the
    # user delete.
    await db.execute(delete(Swipe).where(or_(Swipe.from_user_id == user.id, Swipe.to_user_id == user.id)))
    await db.execute(delete(Match).where(or_(Match.user_a_id == user.id, Match.user_b_id == user.id)))
    await db.execute(delete(Block).where(or_(Block.blocker_id == user.id, Block.blocked_id == user.id)))
    await db.execute(delete(Report).where(or_(Report.reporter_id == user.id, Report.reported_id == user.id)))
    await db.execute(delete(CoupleStoryReport).where(CoupleStoryReport.reporter_id == user.id))
    await db.delete(user)
    await db.commit()
