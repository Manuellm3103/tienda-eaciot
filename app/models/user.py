import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth0_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    picture = Column(String)
    
    # Fidelización
    loyalty_level = Column(String(20), default="bronce")
    loyalty_points = Column(Integer, default=0)
    total_spent = Column(Numeric(10, 2), default=0.00)
    purchase_count = Column(Integer, default=0)
    last_purchase_at = Column(DateTime)
    
    # IA
    is_fidel = Column(Boolean, default=False)
    fidel_score = Column(Integer, default=0)
    
    # Admin
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
