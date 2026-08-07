import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(255))
    comment = Column(Text)
    
    is_verified_purchase = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
