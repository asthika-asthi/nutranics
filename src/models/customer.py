from datetime import datetime
from sqlalchemy import Column, String, Boolean, JSON, Date, DateTime, Text, ForeignKey, Index
from models.base import Base, TimestampMixin, generate_uuid


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id"), nullable=False)
    name = Column(String(200), nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    dob = Column(Date, nullable=True)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    postcode = Column(String(20), nullable=True)
    source = Column(String(100), nullable=True)
    preferred_contact = Column(String(20), nullable=False, default="email")
    health_flags = Column(JSON, nullable=True)
    emergency_contact_name = Column(String(200), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    tags = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_customers_practitioner_id", "practitioner_id"),
        Index("ix_customers_email", "email"),
        Index("ix_customers_is_active", "is_active"),
        Index("ix_customers_created_at", "created_at"),
    )


class CustomerAssignment(Base):
    __tablename__ = "customer_assignments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    assigned_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    can_view = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_customer_assignments_unique", "customer_id", "practitioner_id", unique=True),
        Index("ix_customer_assignments_practitioner_id", "practitioner_id"),
    )
