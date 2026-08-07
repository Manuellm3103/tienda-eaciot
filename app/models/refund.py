import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Refund(Base):
    __tablename__ = "refunds"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    amount = Column(Numeric(10, 2), nullable=False)
    reason = Column(Text)
    
    status = Column(String(50), default="pending")  # pending, approved, processing, completed, rejected
    refund_method = Column(String(50))  # original_payment, store_credit
    
    payment_refund_id = Column(String(255))  # Stripe/PayPal refund ID
    
    admin_notes = Column(Text)
    processed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
