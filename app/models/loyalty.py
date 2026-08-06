import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class LoyaltyHistory(Base):
    __tablename__ = "loyalty_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    points_change = Column(Integer, nullable=False)
    reason = Column(String(255))
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
