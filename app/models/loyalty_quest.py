"""Gamified loyalty quests for AI-powered loyalty (#4.5).

Each quest tracks progress toward a goal (e.g., buy N times, explore a category,
write a review). Completing a quest grants a reward.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from app.database import Base


class LoyaltyQuest(Base):
    __tablename__ = "loyalty_quests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    quest_type = Column(String(50), nullable=False)  # purchase_count, category_explorer, review_writer
    progress = Column(Integer, default=0)
    target = Column(Integer, nullable=False)
    reward_type = Column(String(50), nullable=False)  # points, discount, free_shipping
    reward_value = Column(String(255), nullable=False)  # e.g., "100", "10%", "free"
    expires_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
