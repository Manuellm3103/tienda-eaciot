import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, Boolean, JSON, Integer
from app.database import Base


class ProductBundle(Base):
    __tablename__ = "product_bundles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    product_ids = Column(JSON, nullable=False)  # list[str]
    discount_type = Column(String(20), nullable=False, default="percentage")  # percentage|fixed
    discount_value = Column(Numeric(10, 2), nullable=False, default=15)
    score = Column(Numeric(5, 4), nullable=True)  # confidence 0-1
    ai_generated = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
