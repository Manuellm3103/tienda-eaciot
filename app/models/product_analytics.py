import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database import Base


class ProductAnalytics(Base):
    __tablename__ = "product_analytics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    views_24h = Column(Integer, default=0)
    cart_adds_24h = Column(Integer, default=0)
    sales_24h = Column(Integer, default=0)
    sales_30d = Column(Integer, default=0)
    avg_views_30d = Column(Integer, default=0)
    recorded_at = Column(DateTime, default=datetime.utcnow)
