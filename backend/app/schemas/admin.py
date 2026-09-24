import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.services.storage_service import build_public_url


class ReportAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    reporter_id: uuid.UUID
    reported_id: uuid.UUID
    reason: str
    detail: str | None
    status: str
    created_at: datetime
    reporter_name: str | None = None
    reported_name: str | None = None


class ReportActionRequest(BaseModel):
    # 'warn' bumps the reported user's warning_count; 'ban' sets is_banned;
    # 'dismiss' just closes the report with no action against the user.
    action: str = Field(pattern="^(warn|ban|dismiss)$")
    note: str | None = Field(default=None, max_length=1000)


class ConversationMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    match_id: uuid.UUID
    sender_id: uuid.UUID
    sender_name: str | None = None
    content: str
    message_type: str
    image_object_path: str | None = Field(exclude=True, default=None)
    sent_at: datetime

    @computed_field
    @property
    def image_url(self) -> str | None:
        return build_public_url(self.image_object_path) if self.image_object_path else None


class InquiryAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    user_name: str | None = None
    subject: str
    message: str
    status: str
    admin_note: str | None
    created_at: datetime
    resolved_at: datetime | None


class InquiryResolveRequest(BaseModel):
    admin_note: str | None = Field(default=None, max_length=1000)


class DailyCount(BaseModel):
    day: date
    count: int


class PromotionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: str
    product_name: str | None = None
    discount_percent: int
    is_active: bool
    created_at: datetime


class PromotionCreateRequest(BaseModel):
    product_id: str
    discount_percent: int = Field(ge=1, le=95)


class DashboardStatsOut(BaseModel):
    total_users: int
    new_users_today: int
    new_users_7d: int
    new_users_30d: int
    signups_by_day: list[DailyCount]
    total_reports: int
    open_reports: int
    total_matches: int
    active_matches: int
    total_messages: int
    messages_today: int
    premium_users: int
    banned_users: int
    pending_face_verifications: int
    new_inquiries: int
    total_revenue_cents_30d: int
    active_today: int
    reported_users: int
    churned_users: int
    churn_rate_pct: float


class DemographicBucket(BaseModel):
    key: str
    count: int


class GenderSplitBucket(BaseModel):
    key: str
    male: int
    female: int
    other: int


class DemographicsOut(BaseModel):
    gender: list[DemographicBucket]
    race_ethnicity: list[DemographicBucket]
    religion: list[DemographicBucket]
    political_view: list[DemographicBucket]
    education: list[DemographicBucket]
    smoking: list[DemographicBucket]
    cannabis: list[DemographicBucket]
    exercise_frequency: list[DemographicBucket]
    relationship_goal: list[DemographicBucket]
    wants_kids: list[DemographicBucket]
    has_kids: list[DemographicBucket]
    mbti: list[GenderSplitBucket]
    height_cm: list[DemographicBucket]
    verified_badge: list[DemographicBucket]
    premium_member: list[DemographicBucket]


class TimeseriesPoint(BaseModel):
    day: date
    count: int


class TimeseriesOut(BaseModel):
    points: list[TimeseriesPoint]
    total_in_period: int
    # None only when there's no comparable prior period to diff against
    # (period="all", or a brand-new app with no history before this window).
    pct_change: float | None
