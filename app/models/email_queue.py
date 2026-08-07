import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text
from app.database import Base


class EmailQueue(Base):
    __tablename__ = "email_queue"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    to_email = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    html_content = Column(Text, nullable=False)
    
    status = Column(String(20), default="pending")  # pending, sent, failed
    attempts = Column(Integer, default=0)
    last_error = Column(String(255), nullable=True)
    
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
