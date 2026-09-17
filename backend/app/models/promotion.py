import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Unicode, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Promotion(Base):
    """An admin-created discount on one PRODUCTS catalog entry (see
    services/payment_service.py) — activating one broadcasts a push
    notification to every device with a registered token (see
    push_service.send_promo_broadcast_notification) and discounts that
    product's Stripe Checkout price until deactivated. At most one active
    row per product_id at a time (enforced in routers/admin.py, not here —
    activating a new one for the same product deactivates the old one)."""

    __tablename__ = "Promotions"

    id: Mapped[uuid.UUID] = mapped_column("Id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[str] = mapped_column("ProductId", Unicode(100), nullable=False)
    discount_percent: Mapped[int] = mapped_column("DiscountPercent", Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column("IsActive", Boolean, default=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        "CreatedBy", ForeignKey("Users.Id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column("CreatedAt", DateTime(timezone=True), server_default=func.now())
