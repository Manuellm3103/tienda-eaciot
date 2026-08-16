"""Audit log for agentic actions (e.g., checkout flows).

Each row records a step taken by an autonomous agent so the flow can be
reviewed, debugged, and rolled back if necessary.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from app.database import Base


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    agent_name = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
