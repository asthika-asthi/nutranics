from datetime import datetime
from sqlalchemy import Column, String, Numeric, Date, DateTime, JSON, Text, ForeignKey, Index
from models.base import Base, TimestampMixin, generate_uuid


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    invoice_number = Column(String(50), nullable=False, unique=True)
    date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    total = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    payment_id = Column(String(36), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    line_items = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)
    business_name = Column(String(200), nullable=True)
    business_address = Column(String(500), nullable=True)
    customer_name = Column(String(200), nullable=False)
    customer_address = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_invoices_invoice_number", "invoice_number"),
        Index("ix_invoices_customer_id", "customer_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_date", "date"),
    )
