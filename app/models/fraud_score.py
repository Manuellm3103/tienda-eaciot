import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Text, DateTime, ForeignKey
from app.database import Base


class FraudScore(Base):
    """AI fraud risk score attached to an order at creation time."""

    __tablename__ = "fraud_scores"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high
    features_json = Column(Text, nullable=True)
    flags_json = Column(Text, nullable=True)
    auto_decision = Column(String(20), nullable=False)  # approved, flagged, blocked
    reviewed_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
