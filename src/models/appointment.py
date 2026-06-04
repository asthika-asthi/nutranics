from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, Text, Date, Time, DateTime, ForeignKey, CheckConstraint, Index
from models.base import Base, TimestampMixin, generate_uuid


class Room(Base):
    __tablename__ = "rooms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)


class PractitionerAvailability(Base):
    __tablename__ = "practitioner_availability"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_practitioner_availability_unique", "practitioner_id", "day_of_week", unique=True),
    )


class PractitionerAbsence(Base):
    __tablename__ = "practitioner_absences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False)
    absence_type = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    all_day = Column(Boolean, nullable=False, default=True)
    reason = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_practitioner_absences_dates", "practitioner_id", "start_date", "end_date"),
        CheckConstraint("end_date >= start_date", name="ck_absences_end_date"),
    )


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id"), nullable=False)
    plan_slot_id = Column(String(36), nullable=True)
    type = Column(String(30), nullable=False)
    location = Column(String(20), nullable=False, default="clinic")
    address = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="scheduled")
    scheduled_at = Column(DateTime, nullable=False)
    duration_mins = Column(Integer, nullable=False, default=60)
    notes = Column(Text, nullable=True)
    is_plan_generated = Column(Boolean, nullable=False, default=False)
    parent_appointment_id = Column(String(36), ForeignKey("appointments.id"), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_appointments_customer_id", "customer_id"),
        Index("ix_appointments_practitioner_id", "practitioner_id"),
        Index("ix_appointments_scheduled_at", "scheduled_at"),
        Index("ix_appointments_status", "status"),
        Index("ix_appointments_plan_slot_id", "plan_slot_id", unique=True),
        CheckConstraint("duration_mins > 0", name="ck_appointments_duration"),
    )
