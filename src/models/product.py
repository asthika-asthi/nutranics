from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, DateTime, ForeignKey, Index
from models.base import Base, TimestampMixin, generate_uuid


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(200), nullable=False)
    sku = Column(String(100), nullable=False, unique=True)
    category = Column(String(30), nullable=False)
    description = Column(Text, nullable=True)
    cost_price = Column(Numeric(10, 2), nullable=False)
    retail_price = Column(Numeric(10, 2), nullable=False)
    stock_level = Column(Integer, nullable=False, default=0)
    reorder_threshold = Column(Integer, nullable=False, default=10)
    supplier = Column(String(200), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_products_sku", "sku"),
        Index("ix_products_category", "category"),
        Index("ix_products_is_active", "is_active"),
        Index("ix_products_stock_level", "stock_level"),
    )


class ProductTransaction(Base):
    __tablename__ = "product_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    transaction_type = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_product_transactions_product_id", "product_id"),
        Index("ix_product_transactions_order_id", "order_id"),
        Index("ix_product_transactions_created_at", "created_at"),
    )
