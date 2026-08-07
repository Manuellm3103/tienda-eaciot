import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from app.database import Base


class Wishlist(Base):
    __tablename__ = "wishlists"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
