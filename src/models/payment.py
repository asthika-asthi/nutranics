from datetime import datetime
from sqlalchemy import Column, String, Numeric, Date, DateTime, Text, ForeignKey, Index
from models.base import Base, generate_uuid


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    subscription_id = Column(String(36), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    method = Column(String(20), nullable=False)
    reference = Column(String(200), nullable=True)
    date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_payments_customer_id", "customer_id"),
        Index("ix_payments_subscription_id", "subscription_id"),
        Index("ix_payments_invoice_id", "invoice_id"),
        Index("ix_payments_date", "date"),
    )
