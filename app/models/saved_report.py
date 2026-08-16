import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime
from app.database import Base


class SavedReport(Base):
    __tablename__ = "saved_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    question = Column(Text, nullable=False)
    sql = Column(Text, nullable=False)
    chart_type = Column(String(20), default="table")
    created_at = Column(DateTime, default=datetime.utcnow)
