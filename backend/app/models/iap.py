import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentTransaction(Base):
    """Records a completed Stripe Checkout session so its webhook can never
    double-grant credits on redelivery (unique on stripe_event_id)."""

    __tablename__ = "payment_transactions"
    __table_args__ = (UniqueConstraint("stripe_event_id", name="uq_payment_stripe_event_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    stripe_event_id: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    stripe_session_id: Mapped[str] = mapped_column(Unicode(255), nullable=False)
    product_id: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    credit_kind: Mapped[str] = mapped_column(Unicode(20), nullable=False)  # 'superlike' | 'boost'
    credits_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
