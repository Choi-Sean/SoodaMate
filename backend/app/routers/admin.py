from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import cast, func, or_, select, Date as SqlDate
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models.inquiry import ContactInquiry
from app.models.interaction import Match, Report
from app.models.message import Message
from app.models.iap import PaymentTransaction
from app.models.profile import FaceVerification, Profile
from app.models.promotion import Promotion
from app.models.user import User
from app.schemas.admin import (
    ConversationMessageOut,
    DailyCount,
    DashboardStatsOut,
    InquiryAdminOut,
    InquiryResolveRequest,
    PromotionCreateRequest,
    PromotionOut,
    ReportActionRequest,
    ReportAdminOut,
)
from app.schemas.verification import FaceVerificationAdminOut, FaceVerificationRejectRequest
from app.services import push_service
from app.services.payment_service import PRODUCTS
from app.utils.premium import is_premium

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/face-verifications", response_model=list[FaceVerificationAdminOut])
async def list_face_verifications(
    status_filter: str = Query(default="pending", alias="status", pattern="^(pending|approved|rejected|all)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[FaceVerificationAdminOut]:
    stmt = select(FaceVerification, Profile.display_name).join(
        Profile, Profile.user_id == FaceVerification.user_id, isouter=True
    )
    if status_filter != "all":
        stmt = stmt.where(FaceVerification.status == status_filter)
    stmt = stmt.order_by(FaceVerification.submitted_at.desc())

    rows = (await db.execute(stmt)).all()
    out = []
    for verification, display_name in rows:
        item = FaceVerificationAdminOut.model_validate(verification)
        item.display_name = display_name
        out.append(item)
    return out


async def _get_verification_or_404(db: AsyncSession, verification_id) -> FaceVerification:
    row = await db.get(FaceVerification, verification_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "verification not found")
    return row


@router.post("/face-verifications/{verification_id}/approve", status_code=204)
async def approve_face_verification(
    verification_id,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    from datetime import datetime, timezone

    verification = await _get_verification_or_404(db, verification_id)
    verification.status = "approved"
    verification.reviewed_at = datetime.now(timezone.utc)
    verification.rejection_reason = None
    verification.rejection_reason_key = None
    profile = await db.get(Profile, verification.user_id)
    if profile is not None:
        profile.face_verified = True
    await db.commit()
    await push_service.send_verification_result_notification(db, verification.user_id, approved=True)


@router.post("/face-verifications/{verification_id}/reject", status_code=204)
async def reject_face_verification(
    verification_id,
    body: FaceVerificationRejectRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    from datetime import datetime, timezone

    verification = await _get_verification_or_404(db, verification_id)
    verification.status = "rejected"
    verification.reviewed_at = datetime.now(timezone.utc)
    verification.rejection_reason = body.reason
    verification.rejection_reason_key = body.reason_key
    profile = await db.get(Profile, verification.user_id)
    if profile is not None:
        profile.face_verified = False
    await db.commit()
    await push_service.send_verification_result_notification(db, verification.user_id, approved=False)


# --- Reports -----------------------------------------------------------


@router.get("/reports", response_model=list[ReportAdminOut])
async def list_reports(
    status_filter: str = Query(default="open", alias="status", pattern="^(open|warned|banned|dismissed|all)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[ReportAdminOut]:
    reporter_profile = Profile.__table__.alias("reporter_profile")
    reported_profile = Profile.__table__.alias("reported_profile")
    stmt = (
        select(Report, reporter_profile.c.DisplayName, reported_profile.c.DisplayName)
        .join(reporter_profile, reporter_profile.c.UserId == Report.reporter_id, isouter=True)
        .join(reported_profile, reported_profile.c.UserId == Report.reported_id, isouter=True)
    )
    if status_filter != "all":
        stmt = stmt.where(Report.status == status_filter)
    stmt = stmt.order_by(Report.created_at.desc())

    rows = (await db.execute(stmt)).all()
    out = []
    for report, reporter_name, reported_name in rows:
        item = ReportAdminOut.model_validate(report)
        item.reporter_name = reporter_name
        item.reported_name = reported_name
        out.append(item)
    return out


async def _get_report_or_404(db: AsyncSession, report_id) -> Report:
    row = await db.get(Report, report_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report not found")
    return row


@router.get("/reports/{report_id}/conversation", response_model=list[ConversationMessageOut])
async def get_report_conversation(
    report_id,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[ConversationMessageOut]:
    """Every message from every match the two parties in this report have
    ever had with each other, oldest first — the report itself doesn't
    pin a specific match_id (it predates that idea), so this looks matches
    up by the (reporter, reported) pair instead, which also naturally
    covers a pair that matched more than once."""
    report = await _get_report_or_404(db, report_id)
    match_ids = (
        await db.scalars(
            select(Match.id).where(
                or_(
                    (Match.user_a_id == report.reporter_id) & (Match.user_b_id == report.reported_id),
                    (Match.user_a_id == report.reported_id) & (Match.user_b_id == report.reporter_id),
                )
            )
        )
    ).all()
    if not match_ids:
        return []

    sender_profile = Profile.__table__.alias("sender_profile")
    stmt = (
        select(Message, sender_profile.c.DisplayName)
        .join(sender_profile, sender_profile.c.UserId == Message.sender_id, isouter=True)
        .where(Message.match_id.in_(match_ids))
        .order_by(Message.sent_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    out = []
    for message, sender_name in rows:
        item = ConversationMessageOut.model_validate(message)
        item.sender_name = sender_name
        out.append(item)
    return out


@router.post("/reports/{report_id}/action", status_code=204)
async def act_on_report(
    report_id,
    body: ReportActionRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    report = await _get_report_or_404(db, report_id)
    if body.action in ("warn", "ban"):
        target = await db.get(User, report.reported_id)
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "reported user not found")
        if body.action == "warn":
            target.warning_count += 1
        else:
            target.is_banned = True

    report.status = "warned" if body.action == "warn" else "banned" if body.action == "ban" else "dismissed"
    await db.commit()


# --- Contact inquiries ---------------------------------------------------


@router.get("/inquiries", response_model=list[InquiryAdminOut])
async def list_inquiries(
    status_filter: str = Query(default="all", alias="status", pattern="^(new|read|resolved|all)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[InquiryAdminOut]:
    user_profile = Profile.__table__.alias("user_profile")
    stmt = (
        select(ContactInquiry, user_profile.c.DisplayName)
        .join(user_profile, user_profile.c.UserId == ContactInquiry.user_id, isouter=True)
    )
    if status_filter != "all":
        stmt = stmt.where(ContactInquiry.status == status_filter)
    stmt = stmt.order_by(ContactInquiry.created_at.desc())

    rows = (await db.execute(stmt)).all()
    out = []
    for inquiry, user_name in rows:
        item = InquiryAdminOut.model_validate(inquiry)
        item.user_name = user_name
        out.append(item)
    return out


@router.post("/inquiries/{inquiry_id}/read", status_code=204)
async def mark_inquiry_read(
    inquiry_id,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    inquiry = await db.get(ContactInquiry, inquiry_id)
    if inquiry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "inquiry not found")
    if inquiry.status == "new":
        inquiry.status = "read"
        await db.commit()


@router.post("/inquiries/{inquiry_id}/resolve", status_code=204)
async def resolve_inquiry(
    inquiry_id,
    body: InquiryResolveRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    inquiry = await db.get(ContactInquiry, inquiry_id)
    if inquiry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "inquiry not found")
    inquiry.status = "resolved"
    inquiry.admin_note = body.admin_note
    inquiry.resolved_at = datetime.now(timezone.utc)
    await db.commit()


# --- Dashboard stats -------------------------------------------------------


@router.get("/stats", response_model=DashboardStatsOut)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> DashboardStatsOut:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    total_users = await db.scalar(select(func.count()).select_from(User)) or 0
    new_users_today = await db.scalar(select(func.count()).where(User.created_at >= today_start)) or 0
    new_users_7d = await db.scalar(select(func.count()).where(User.created_at >= since_7d)) or 0
    new_users_30d = await db.scalar(select(func.count()).where(User.created_at >= since_30d)) or 0
    banned_users = await db.scalar(select(func.count()).where(User.is_banned)) or 0

    day_col = cast(User.created_at, SqlDate)
    signup_rows = (
        await db.execute(
            select(day_col.label("day"), func.count().label("count"))
            .where(User.created_at >= since_30d)
            .group_by(day_col)
            .order_by(day_col)
        )
    ).all()
    signups_by_day = [DailyCount(day=row.day, count=row.count) for row in signup_rows]

    total_reports = await db.scalar(select(func.count()).select_from(Report)) or 0
    open_reports = await db.scalar(select(func.count()).where(Report.status == "open")) or 0

    total_matches = await db.scalar(select(func.count()).select_from(Match)) or 0
    active_matches = await db.scalar(select(func.count()).where(Match.is_active)) or 0

    total_messages = await db.scalar(select(func.count()).select_from(Message)) or 0
    messages_today = await db.scalar(select(func.count()).where(Message.sent_at >= today_start)) or 0

    premium_until_rows = (await db.scalars(select(Profile.premium_until).where(Profile.premium_until.isnot(None)))).all()
    premium_users = sum(1 for pu in premium_until_rows if is_premium(pu))

    pending_face_verifications = (
        await db.scalar(select(func.count()).where(FaceVerification.status == "pending")) or 0
    )
    new_inquiries = await db.scalar(select(func.count()).where(ContactInquiry.status == "new")) or 0

    recent_tx = (
        await db.scalars(
            select(PaymentTransaction.product_id).where(PaymentTransaction.created_at >= since_30d)
        )
    ).all()
    total_revenue_cents_30d = sum(PRODUCTS.get(pid, {}).get("price_usd_cents", 0) for pid in recent_tx)

    return DashboardStatsOut(
        total_users=total_users,
        new_users_today=new_users_today,
        new_users_7d=new_users_7d,
        new_users_30d=new_users_30d,
        signups_by_day=signups_by_day,
        total_reports=total_reports,
        open_reports=open_reports,
        total_matches=total_matches,
        active_matches=active_matches,
        total_messages=total_messages,
        messages_today=messages_today,
        premium_users=premium_users,
        banned_users=banned_users,
        pending_face_verifications=pending_face_verifications,
        new_inquiries=new_inquiries,
        total_revenue_cents_30d=total_revenue_cents_30d,
    )


# --- Promotions -------------------------------------------------------


@router.get("/promotions", response_model=list[PromotionOut])
async def list_promotions(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[PromotionOut]:
    rows = (await db.scalars(select(Promotion).order_by(Promotion.created_at.desc()))).all()
    out = []
    for promo in rows:
        item = PromotionOut.model_validate(promo)
        product = PRODUCTS.get(promo.product_id)
        item.product_name = product["name"] if product else promo.product_id
        out.append(item)
    return out


@router.post("/promotions", response_model=PromotionOut, status_code=201)
async def create_promotion(
    body: PromotionCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> PromotionOut:
    product = PRODUCTS.get(body.product_id)
    if product is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown product_id")

    # Only one active discount per product at a time — activating a new one
    # supersedes whatever was already running for it, rather than stacking.
    existing_active = (
        await db.scalars(
            select(Promotion).where(Promotion.product_id == body.product_id, Promotion.is_active)
        )
    ).all()
    for promo in existing_active:
        promo.is_active = False

    promotion = Promotion(product_id=body.product_id, discount_percent=body.discount_percent, created_by=admin.id)
    db.add(promotion)
    await db.commit()
    await db.refresh(promotion)

    await push_service.send_promo_broadcast_notification(db, body.product_id, body.discount_percent)

    item = PromotionOut.model_validate(promotion)
    item.product_name = product["name"]
    return item


@router.post("/promotions/{promotion_id}/deactivate", status_code=204)
async def deactivate_promotion(
    promotion_id,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    promotion = await db.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "promotion not found")
    promotion.is_active = False
    await db.commit()
