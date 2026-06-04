from datetime import datetime
from sqlalchemy import Column, String, Date, Numeric, Integer, ForeignKey, DateTime, Text, CheckConstraint, Index
from models.base import Base, TimestampMixin, generate_uuid


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String(36), ForeignKey("plans.id"), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    start_date = Column(Date, nullable=False)
    billing_day = Column(Integer, nullable=False)
    next_billing_date = Column(Date, nullable=False)
    months_billed = Column(Integer, nullable=False, default=0)
    paused_at = Column(Date, nullable=True)
    pause_resume_date = Column(Date, nullable=True)
    cancelled_at = Column(Date, nullable=True)
    cancel_reason = Column(Text, nullable=True)
    cancellation_fee = Column(Numeric(10, 2), nullable=True)
    initial_prorata_amount = Column(Numeric(10, 2), nullable=True)
    total_billed = Column(Numeric(10, 2), nullable=False, default=0)
    total_paid = Column(Numeric(10, 2), nullable=False, default=0)
    current_cycle_start = Column(Date, nullable=False)
    current_cycle_end = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_subscriptions_customer_id", "customer_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_next_billing_date", "next_billing_date"),
        CheckConstraint("billing_day >= 1 AND billing_day <= 31", name="ck_subscriptions_billing_day"),
    )


class PlanSlot(Base):
    __tablename__ = "plan_slots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    plan_item_id = Column(String(36), ForeignKey("plan_items.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(50), nullable=False)
    item_name = Column(String(200), nullable=False)
    suggested_date = Column(Date, nullable=False)
    booking_window_start = Column(Date, nullable=False)
    booking_window_end = Column(Date, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    appointment_id = Column(
        String(36),
        ForeignKey("appointments.id", use_alter=True, name="fk_plan_slots_appointment_id"),
        nullable=True,
        unique=True,
    )
    missed_reason = Column(Text, nullable=True)
    missed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_plan_slots_subscription_id", "subscription_id"),
        Index("ix_plan_slots_status", "status"),
        Index("ix_plan_slots_suggested_date", "suggested_date"),
        Index("ix_plan_slots_booking_window_start", "booking_window_start"),
    )
