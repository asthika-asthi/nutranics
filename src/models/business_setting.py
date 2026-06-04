from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Boolean
from models.base import Base, generate_uuid


class BusinessSetting(Base):
    __tablename__ = "business_settings"

    id = Column(Integer, primary_key=True, default=1)
    business_name = Column(String(200), nullable=False)
    business_address = Column(Text, nullable=False)
    business_phone = Column(String(20), nullable=True)
    business_email = Column(String(255), nullable=True)
    tax_rate = Column(Numeric(5, 4), nullable=False, default=0.0)
    invoice_prefix = Column(String(10), nullable=False, default="INV")
    next_invoice_number = Column(Integer, nullable=False, default=1)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password_encrypted = Column(String(255), nullable=True)
    smtp_from_email = Column(String(255), nullable=True)
    smtp_from_name = Column(String(200), nullable=True)
    plan_slot_reminder_days = Column(Integer, nullable=False, default=7)
    appointment_reminder_48h = Column(Boolean, nullable=False, default=True)
    max_home_visits_per_day = Column(Integer, nullable=False, default=2)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
