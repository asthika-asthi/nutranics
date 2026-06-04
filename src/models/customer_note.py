from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Index
from models.base import Base, generate_uuid


class CustomerNote(Base):
    __tablename__ = "customer_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id"), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(20), nullable=False, default="general")
    is_synced = Column(Boolean, nullable=False, default=True)
    sync_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False)
    server_created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_customer_notes_customer_id", "customer_id"),
        Index("ix_customer_notes_practitioner_id", "practitioner_id"),
        Index("ix_customer_notes_created_at", "created_at"),
        Index("ix_customer_notes_is_synced", "is_synced"),
    )
