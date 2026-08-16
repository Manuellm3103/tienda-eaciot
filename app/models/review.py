import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)

    product = relationship("Product")

    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(255))
    comment = Column(Text)
    
    is_verified_purchase = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)

    sentiment_score = Column(Float, nullable=True)  # -1 (negative) to 1 (positive)
    sentiment_label = Column(String(20), nullable=True)  # positive, neutral, negative
    ai_response = Column(Text, nullable=True)
    ai_response_approved = Column(Boolean, default=False)
    ai_responded_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
