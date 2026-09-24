import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, case, cast, func, or_, select, Date as SqlDate, Integer
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
    DemographicBucket,
    DemographicsOut,
    GenderSplitBucket,
    InquiryAdminOut,
    InquiryResolveRequest,
    PromotionCreateRequest,
    PromotionOut,
    ReportActionRequest,
    ReportAdminOut,
    TimeseriesOut,
    TimeseriesPoint,
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
    stmt = select(FaceVerification, Profile.display_name, Profile.legal_first_name, Profile.birth_date).join(
        Profile, Profile.user_id == FaceVerification.user_id, isouter=True
    )
    if status_filter != "all":
        stmt = stmt.where(FaceVerification.status == status_filter)
    stmt = stmt.order_by(FaceVerification.submitted_at.desc())

    rows = (await db.execute(stmt)).all()
    out = []
    for verification, display_name, legal_first_name, birth_date in rows:
        item = FaceVerificationAdminOut.model_validate(verification)
        item.display_name = display_name
        item.legal_first_name = legal_first_name
        item.birth_date = birth_date
        out.append(item)
    return out


async def _get_verification_or_404(db: AsyncSession, verification_id) -> FaceVerification:
    row = await db.get(FaceVerification, verification_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "verification not found")
    return row


@router.post("/face-verifications/{verification_id}/approve", status_code=204)
async def approve_face_verification(
    verification_id: uuid.UUID,
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
    verification_id: uuid.UUID,
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
    report_id: uuid.UUID,
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
    report_id: uuid.UUID,
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
    inquiry_id: uuid.UUID,
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
    inquiry_id: uuid.UUID,
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


def _actual_amount_cents(raw_payload: str) -> int:
    """The real amount actually charged for one PaymentTransaction, read
    straight from the Stripe webhook payload it was recorded from —
    PaymentTransaction has no dedicated "amount paid" column of its own, and
    re-deriving revenue from PRODUCTS[product_id]["price_usd_cents"] (the
    undiscounted list price) is exactly what made the dashboard's 30-day
    revenue figure wrong whenever a Promotion discount applied (see
    payment_service.py's Promotion/discount machinery) — a $2.99 item bought
    at 50% off shows here as $2.99, not the $1 actually charged.
    checkout.session.completed events carry amount_total; the recurring
    invoice.paid/invoice.payment_succeeded events (subsequent membership
    billing cycles) carry amount_paid instead - both already in cents."""
    try:
        obj = json.loads(raw_payload)["data"]["object"]
    except (ValueError, KeyError, TypeError):
        return 0
    amount = obj.get("amount_total")
    if amount is None:
        amount = obj.get("amount_paid")
    return int(amount) if isinstance(amount, (int, float)) else 0


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

    recent_tx_payloads = (
        await db.scalars(
            select(PaymentTransaction.raw_payload).where(PaymentTransaction.created_at >= since_30d)
        )
    ).all()
    total_revenue_cents_30d = sum(_actual_amount_cents(p) for p in recent_tx_payloads)

    active_today = await db.scalar(select(func.count()).where(User.last_active_at >= today_start)) or 0

    # Distinct users who have ever been the *target* of a report, regardless
    # of that report's current status (open/warned/banned/dismissed) — a
    # different number from open_reports above, which counts report rows,
    # not distinct people.
    reported_users = await db.scalar(select(func.count(func.distinct(Report.reported_id)))) or 0

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
        active_today=active_today,
        reported_users=reported_users,
    )


# --- Demographics -------------------------------------------------------


async def _bucket_counts(db: AsyncSession, column) -> list[DemographicBucket]:
    """GROUP BY on one nullable free-text Profile dimension (race_ethnicity,
    religion, education, ...) — NULL (never filled in) becomes its own
    "not_set" bucket rather than being silently dropped, since "how many
    profiles haven't set this yet" is itself useful to an admin. Ordered
    largest-first so the dashboard's biggest segments show up first.

    Grouped via a subquery, not `GROUP BY coalesce(column, 'not_set')`
    directly: MSSQL prepares COALESCE(col, ?) in the SELECT list and the
    identical-looking one in GROUP BY as two separately bound parameters
    (each occurrence gets its own `?` placeholder even though both are bound
    to the same literal at execute time) and refuses to treat them as the
    same expression — "column is invalid in the select list because it is
    not contained in ... the GROUP BY clause" even though it very much is.
    Grouping by the subquery's own materialized `key` column sidesteps the
    ambiguity entirely; Postgres has no such issue either way."""
    inner = select(func.coalesce(column, "not_set").label("key")).subquery()
    rows = (
        await db.execute(
            select(inner.c.key, func.count().label("count")).group_by(inner.c.key).order_by(func.count().desc())
        )
    ).all()
    return [DemographicBucket(key=row.key, count=row.count) for row in rows]


@router.get("/demographics", response_model=DemographicsOut)
async def get_demographics(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> DemographicsOut:
    gender = await _bucket_counts(db, Profile.gender)
    race_ethnicity = await _bucket_counts(db, Profile.race_ethnicity)
    religion = await _bucket_counts(db, Profile.religion)
    political_view = await _bucket_counts(db, Profile.political_view)
    education = await _bucket_counts(db, Profile.education)
    smoking = await _bucket_counts(db, Profile.smoking)
    cannabis = await _bucket_counts(db, Profile.cannabis)
    exercise_frequency = await _bucket_counts(db, Profile.exercise_frequency)
    relationship_goal = await _bucket_counts(db, Profile.relationship_goal)
    wants_kids = await _bucket_counts(db, Profile.wants_kids)
    has_kids = await _bucket_counts(db, Profile.has_kids)
    verified_badge = await _bucket_counts(db, Profile.verified_badge)

    # MBTI, split by gender (male/female/other counts per type) — the exact
    # shape asked for ("mbti ㅇㅇㅇ인사람은 몇명, 여자는 몇, 남자는 몇"). Grouped
    # via a subquery, same reason as _bucket_counts above (MSSQL rejects
    # GROUP BY on a repeated-with-a-literal expression like this).
    mbti_inner = select(
        func.coalesce(Profile.mbti, "not_set").label("mbti"), Profile.gender.label("gender")
    ).subquery()
    mbti_rows = (
        await db.execute(
            select(mbti_inner.c.mbti, mbti_inner.c.gender, func.count().label("count")).group_by(
                mbti_inner.c.mbti, mbti_inner.c.gender
            )
        )
    ).all()
    mbti_by_key: dict[str, dict[str, int]] = {}
    for row in mbti_rows:
        bucket = mbti_by_key.setdefault(row.mbti, {"male": 0, "female": 0, "other": 0})
        if row.gender in bucket:
            bucket[row.gender] += row.count
    mbti = [
        GenderSplitBucket(key=key, male=v["male"], female=v["female"], other=v["other"])
        for key, v in sorted(mbti_by_key.items(), key=lambda kv: sum(kv[1].values()), reverse=True)
    ]

    # 5cm-wide buckets ("170"-"174" -> key "170"). The `/ 5` here is NOT
    # reliably integer division on MSSQL: the literal 5 goes over the wire as
    # a bound ODBC parameter, which pyodbc/MSSQL can infer as DECIMAL rather
    # than INT, silently turning this into float division (172/5 -> 34.4,
    # not 34) — Postgres has no such ambiguity either way. Wrapping the
    # division in an explicit Integer cast truncates it back to a whole
    # bucket index regardless of which kind of division actually ran, so
    # this is correct on both dialects. Same subquery treatment as above for
    # the same MSSQL GROUP BY reason.
    height_inner = select(
        case(
            (Profile.height_cm.is_(None), None),
            else_=cast(Profile.height_cm / 5, Integer) * 5,
        ).label("bucket")
    ).subquery()
    height_rows = (
        await db.execute(
            select(height_inner.c.bucket, func.count().label("count"))
            .group_by(height_inner.c.bucket)
            .order_by(height_inner.c.bucket)
        )
    ).all()
    height_cm = [
        DemographicBucket(key=f"{row.bucket}-{row.bucket + 4}" if row.bucket is not None else "not_set", count=row.count)
        for row in height_rows
    ]

    premium_inner = select(
        case(
            (and_(Profile.premium_until.isnot(None), Profile.premium_until > func.now()), "premium"),
            else_="free",
        ).label("key")
    ).subquery()
    premium_rows = (
        await db.execute(
            select(premium_inner.c.key, func.count().label("count")).group_by(premium_inner.c.key)
        )
    ).all()
    premium_member = [DemographicBucket(key=row.key, count=row.count) for row in premium_rows]

    return DemographicsOut(
        gender=gender,
        race_ethnicity=race_ethnicity,
        religion=religion,
        political_view=political_view,
        education=education,
        smoking=smoking,
        cannabis=cannabis,
        exercise_frequency=exercise_frequency,
        relationship_goal=relationship_goal,
        wants_kids=wants_kids,
        has_kids=has_kids,
        mbti=mbti,
        height_cm=height_cm,
        verified_badge=verified_badge,
        premium_member=premium_member,
    )


# --- Timeseries (stock-chart-style period picker) ------------------------

_PERIOD_DAYS = {"1w": 7, "1m": 30, "3m": 90, "1y": 365, "3y": 365 * 3}


def _period_start(period: str, now: datetime) -> datetime | None:
    """None means "from the beginning" (period="all") — the caller skips the
    lower bound entirely rather than trying to express "negative infinity"
    as a datetime."""
    if period == "ytd":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    if period == "all":
        return None
    days = _PERIOD_DAYS.get(period)
    if days is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown period")
    return now - timedelta(days=days)


async def _daily_counts(db: AsyncSession, date_column, start: datetime | None, end: datetime) -> list[TimeseriesPoint]:
    day_col = cast(date_column, SqlDate)
    where = [date_column < end]
    if start is not None:
        where.append(date_column >= start)
    rows = (
        await db.execute(
            select(day_col.label("day"), func.count().label("count")).where(*where).group_by(day_col).order_by(day_col)
        )
    ).all()
    return [TimeseriesPoint(day=row.day, count=row.count) for row in rows]


@router.get("/timeseries", response_model=TimeseriesOut)
async def get_timeseries(
    metric: str = Query(pattern="^(signups)$"),
    period: str = Query(default="1m", pattern="^(1w|1m|3m|ytd|1y|3y|all)$"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> TimeseriesOut:
    """Daily counts for the selected window, stock-chart style, plus
    pct_change against the immediately preceding period of the same length
    (this week vs last week, etc.) — period="all"/"ytd" have no well-defined
    "previous period" of the same length, so pct_change is None for those.
    metric is only ever "signups" for now — a "churn" metric is held back
    pending a new AccountDeletionLogs table (see git history/PR notes)."""
    now = datetime.now(timezone.utc)
    start = _period_start(period, now)
    date_column = User.created_at

    async def _count_between(lo: datetime | None, hi: datetime) -> int:
        where = [date_column < hi]
        if lo is not None:
            where.append(date_column >= lo)
        return await db.scalar(select(func.count()).where(*where)) or 0

    points = await _daily_counts(db, date_column, start, now)
    total_in_period = sum(p.count for p in points)

    pct_change: float | None = None
    if period not in ("all", "ytd") and start is not None:
        period_length = now - start
        prev_start = start - period_length
        prev_total = await _count_between(prev_start, start)
        if prev_total > 0:
            pct_change = round(100 * (total_in_period - prev_total) / prev_total, 1)
        elif total_in_period > 0:
            pct_change = 100.0  # from zero to something is a genuine "up", not a divide-by-zero no-op

    return TimeseriesOut(points=points, total_in_period=total_in_period, pct_change=pct_change)


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
    promotion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    promotion = await db.get(Promotion, promotion_id)
    if promotion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "promotion not found")
    promotion.is_active = False
    await db.commit()
