import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, Text, ForeignKey
from app.database import Base


class CongratulationRule(Base):
    __tablename__ = "congratulation_rules"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    event_type = Column(String(50), nullable=False)
    event_value = Column(Numeric(10, 2))
    event_product_id = Column(String(36), ForeignKey("products.id"))
    
    reward_type = Column(String(30), nullable=False)
    reward_value = Column(Numeric(10, 2))
    reward_product_id = Column(String(36), ForeignKey("products.id"))
    
    message_template = Column(Text, nullable=False)
    email_subject = Column(String(255))
    
    is_active = Column(Boolean, default=True)
    max_uses = Column(Integer, default=-1)
    current_uses = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CongratulationHistory(Base):
    __tablename__ = "congratulation_history"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    rule_id = Column(String(36), ForeignKey("congratulation_rules.id"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id"))
    
    message_sent = Column(Text)
    reward_sent = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
