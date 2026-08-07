import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, Text, JSON, ForeignKey
from app.database import Base


class Promotion(Base):
    __tablename__ = "promotions"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Numeric(10, 2), nullable=False)
    
    conditions = Column(JSON)
    
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    
    coupon_code = Column(String(50), unique=True)
    auto_generate_coupons = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    
    ai_suggestion = Column(JSON)
    
    usage_count = Column(Integer, default=0)
    max_uses = Column(Integer, default=-1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Coupon(Base):
    __tablename__ = "coupons"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    
    promotion_id = Column(String(36), ForeignKey("promotions.id"))
    congratulation_rule_id = Column(String(36), ForeignKey("congratulation_rules.id"))
    
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime)
    used_in_order_id = Column(String(36), ForeignKey("orders.id"))
    
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
