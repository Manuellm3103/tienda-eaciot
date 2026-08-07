import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    name = Column(String(255))
    picture = Column(String)
    
    # OAuth providers
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    microsoft_id = Column(String(255), unique=True, nullable=True, index=True)
    github_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Email verification
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    
    # Password reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
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
