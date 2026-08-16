"""Decision log for the AI Marketing Department (#5).

Every routing or action decision taken by the marketing orchestrator is
persisted so outcomes can be measured and fed back into future decisions.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from app.database import Base


class MarketingDecision(Base):
    __tablename__ = "marketing_decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(50), nullable=False)
    task_type = Column(String(50), nullable=False)  # content, seo, campaign, analytics
    decision = Column(Text, nullable=False)
    context = Column(JSON, default=dict)
    outcome = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
