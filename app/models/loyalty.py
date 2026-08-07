import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database import Base


class LoyaltyHistory(Base):
    __tablename__ = "loyalty_history"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    points_change = Column(Integer, nullable=False)
    reason = Column(String(255))
    order_id = Column(String(36), ForeignKey("orders.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
