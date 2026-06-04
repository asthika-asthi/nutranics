from sqlalchemy import Column, String, Boolean, JSON, Index
from models.base import Base, TimestampMixin, generate_uuid


class Practitioner(Base, TimestampMixin):
    __tablename__ = "practitioners"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(20), nullable=False, default="practitioner")
    specialisms = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_practitioners_email", "email"),
        Index("ix_practitioners_role", "role"),
        Index("ix_practitioners_is_active", "is_active"),
    )
