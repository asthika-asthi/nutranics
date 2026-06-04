from datetime import datetime
from sqlalchemy import Column, String, Numeric, Date, DateTime, Text, Boolean, ForeignKey, Index
from models.base import Base, TimestampMixin, generate_uuid


class TestResult(Base, TimestampMixin):
    __tablename__ = "test_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    test_type = Column(String(100), nullable=False)
    date_taken = Column(Date, nullable=False)
    date_received = Column(Date, nullable=True)
    pdf_url = Column(String(500), nullable=True)
    practitioner_notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_test_results_customer_id", "customer_id"),
        Index("ix_test_results_test_type", "test_type"),
        Index("ix_test_results_date_taken", "date_taken"),
        Index("ix_test_results_status", "status"),
    )


class TestMarker(Base):
    __tablename__ = "test_markers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    test_result_id = Column(String(36), ForeignKey("test_results.id", ondelete="CASCADE"), nullable=False)
    marker_name = Column(String(200), nullable=False)
    value = Column(Numeric(10, 4), nullable=True)
    value_text = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=True)
    reference_low = Column(Numeric(10, 4), nullable=True)
    reference_high = Column(Numeric(10, 4), nullable=True)
    is_out_of_range = Column(Boolean, nullable=False, default=False)
    flag = Column(String(20), nullable=False, default="normal")
    practitioner_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_test_markers_test_result_id", "test_result_id"),
        Index("ix_test_markers_marker_name", "marker_name"),
    )


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    test_marker_id = Column(String(36), ForeignKey("test_markers.id", ondelete="SET NULL"), nullable=True)
    recommendation_text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    linked_order_id = Column(String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_recommendations_customer_id", "customer_id"),
        Index("ix_recommendations_status", "status"),
        Index("ix_recommendations_test_marker_id", "test_marker_id"),
    )
