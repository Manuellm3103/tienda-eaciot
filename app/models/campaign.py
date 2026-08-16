import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(
        String(30),
        nullable=False,
        default="seasonal",
    )  # post_purchase, win_back, new_arrival, seasonal, abandoned_cart
    status = Column(
        String(20),
        nullable=False,
        default="draft",
    )  # draft, scheduled, active, paused, completed

    target_audience = Column(JSON, default=dict)
    content = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)

    scheduled_at = Column(DateTime, nullable=True)
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
