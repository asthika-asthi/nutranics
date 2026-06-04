from sqlalchemy import Column, String, Boolean, Text, Numeric, Integer, ForeignKey, Index
from models.base import Base, TimestampMixin, generate_uuid


class Plan(Base, TimestampMixin):
    __tablename__ = "plans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    monthly_price = Column(Numeric(10, 2), nullable=False)
    contract_length = Column(String(50), nullable=False)
    cancellation_terms = Column(Text, nullable=True)
    is_template = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_plans_is_active", "is_active"),
        Index("ix_plans_is_template", "is_template"),
    )


class PlanItem(Base):
    __tablename__ = "plan_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(50), nullable=False)
    item_name = Column(String(200), nullable=False)
    quantity_per_cycle = Column(Integer, nullable=False, default=1)
    frequency = Column(String(50), nullable=False)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_plan_items_plan_id", "plan_id"),
    )
