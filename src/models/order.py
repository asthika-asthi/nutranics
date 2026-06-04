from datetime import datetime
from sqlalchemy import Column, String, Numeric, JSON, DateTime, ForeignKey, Index
from models.base import Base, TimestampMixin, generate_uuid


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True)
    plan_slot_id = Column(String(36), ForeignKey("plan_slots.id", ondelete="SET NULL"), nullable=True)
    items = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    total = Column(Numeric(10, 2), nullable=False)
    shipping_address = Column(String(500), nullable=True)
    fulfilled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_orders_customer_id", "customer_id"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_plan_slot_id", "plan_slot_id"),
    )
