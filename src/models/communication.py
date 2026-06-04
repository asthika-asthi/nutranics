from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index
from models.base import Base, generate_uuid


class CommunicationLog(Base):
    __tablename__ = "communication_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id", ondelete="SET NULL"), nullable=True)
    sent_by_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    channel = Column(String(20), nullable=False)
    type = Column(String(20), nullable=False)
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)
    external_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_communication_logs_customer_id", "customer_id"),
        Index("ix_communication_logs_sent_at", "sent_at"),
        Index("ix_communication_logs_status", "status"),
        Index("ix_communication_logs_channel", "channel"),
    )


class AppointmentReminder(Base):
    __tablename__ = "appointment_reminders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    appointment_id = Column(String(36), ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    reminder_type = Column(String(30), nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_appointment_reminders_appointment_id", "appointment_id"),
        Index("ix_appointment_reminders_scheduled_for", "scheduled_for"),
        Index("ix_appointment_reminders_status", "status"),
    )
