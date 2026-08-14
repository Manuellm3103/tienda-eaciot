import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class UserEvent(Base):
    """Anonymous + identified behavioral events.

    Foundation for the personalization engine (#4) and dynamic pricing (#3):
    each view / cart-add / purchase / wishlist / search is recorded as a row
    so later models can learn per-user and per-product demand.
    """

    __tablename__ = "user_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True, index=True)
    session_id = Column(String(36), nullable=True, index=True)
    # view, cart_add, purchase, wishlist, search
    event_type = Column(String(20), nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
