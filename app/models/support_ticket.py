import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class SupportTicket(Base):
    """A customer support ticket (contact / post-sale question)."""

    __tablename__ = "support_tickets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255))
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    status = Column(String(20), default="open")  # open, in_progress, resolved, closed
    admin_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime)
