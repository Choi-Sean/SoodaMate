import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Unicode, UnicodeText, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentTransaction(Base):
    """Records a completed Stripe Checkout session so its webhook can never
    double-grant credits on redelivery (unique on stripe_event_id)."""

    __tablename__ = "PaymentTransactions"
    __table_args__ = (UniqueConstraint("StripeEventId", name="uq_payment_stripe_event_id"),)

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        "UserId", ForeignKey("Users.Id", ondelete="CASCADE"), nullable=False
    )
    stripe_event_id: Mapped[str] = mapped_column("StripeEventId", Unicode(255), nullable=False)
    stripe_session_id: Mapped[str] = mapped_column("StripeSessionId", Unicode(255), nullable=False)
    product_id: Mapped[str] = mapped_column("ProductId", Unicode(100), nullable=False)
    credit_kind: Mapped[str] = mapped_column("CreditKind", Unicode(20), nullable=False)  # 'superlike' | 'boost'
    credits_granted: Mapped[int] = mapped_column("CreditsGranted", Integer, nullable=False)
    raw_payload: Mapped[str] = mapped_column("RawPayload", UnicodeText, nullable=False)
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
