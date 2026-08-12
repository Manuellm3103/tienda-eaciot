import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    agent_name = Column(String(50))  # which agent produced this (supervisor, product_advisor, copywriter)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
