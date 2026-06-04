from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from models.base import Base, TimestampMixin, generate_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    practitioner_id = Column(String(36), ForeignKey("practitioners.id"), nullable=True, unique=True)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_practitioner_id", "practitioner_id"),
        Index("ix_users_role", "role"),
    )
