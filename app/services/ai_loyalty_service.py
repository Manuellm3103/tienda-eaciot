"""AI-powered Loyalty & Gamification (#4.5 on the innovation roadmap).

Adds churn prediction, personalized retention offers, gamified quests, and
birthday campaigns on top of the existing loyalty service.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Category
from app.models.loyalty_quest import LoyaltyQuest
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.loyalty_service import loyalty_service


class AILoyaltyService:
    HIGH_VALUE_THRESHOLD = Decimal("1000")
    CHURN_DAYS_HIGH = 60
    CHURN_DAYS_MEDIUM = 30

    async def predict_churn_risk(self, db: AsyncSession, user_id: str) -> dict[str, Any]:
        """Score 0-1 likelihood that the user will churn based on RFM signals."""
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        days_since_last_purchase = 0
        if user.last_purchase_at:
            days_since_last_purchase = max(0, (datetime.utcnow() - user.last_purchase_at).days)

        score = 0.0
        if days_since_last_purchase > self.CHURN_DAYS_HIGH:
            score += 0.6
        elif days_since_last_purchase > self.CHURN_DAYS_MEDIUM:
            score += 0.3

        if (user.purchase_count or 0) == 0:
            score += 0.3
        elif (user.purchase_count or 0) == 1:
            score += 0.15

        total_spent = Decimal(user.total_spent or 0)
        if total_spent >= self.HIGH_VALUE_THRESHOLD:
            score -= 0.15
        elif total_spent == 0:
            score += 0.1

        score = max(0.0, min(1.0, score))

        level = "low"
        if score > 0.7:
            level = "high"
        elif score > 0.35:
            level = "medium"

        return {
            "score": round(score, 2),
            "level": level,
            "days_since_last_purchase": days_since_last_purchase,
            "purchase_count": user.purchase_count or 0,
            "total_spent": float(total_spent),
        }

    async def suggest_retention_offer(
        self, db: AsyncSession, user_id: str
    ) -> dict[str, Any]:
        """Generate a personalized retention offer for an at-risk user."""
        risk = await self.predict_churn_risk(db, user_id)
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        favorite_category_name = "tus favoritos"
        if user.favorite_category_id:
            category = await db.get(Category, user.favorite_category_id)
            if category:
                favorite_category_name = category.name

        if risk["level"] == "high":
            discount = 20
            offer_type = "discount"
        elif risk["level"] == "medium":
            discount = 10
            offer_type = "discount"
        else:
            discount = 5
            offer_type = "points"

        return {
            "risk": risk,
            "offer_type": offer_type,
            "discount_percent": discount,
            "message": (
                f"Te extrañamos. Usa {discount}% de descuento en {favorite_category_name} "
                "para tu próxima compra. Válido por 7 días."
            ),
            "valid_days": 7,
        }

    async def get_active_quests(
        self, db: AsyncSession, user_id: str
    ) -> list[LoyaltyQuest]:
        result = await db.execute(
            select(LoyaltyQuest)
            .where(LoyaltyQuest.user_id == user_id)
            .where(LoyaltyQuest.completed_at.is_(None))
            .where(
                (LoyaltyQuest.expires_at.is_(None)) | (LoyaltyQuest.expires_at >= datetime.utcnow())
            )
            .order_by(LoyaltyQuest.created_at.desc())
        )
        return result.scalars().all()

    async def create_quest(
        self,
        db: AsyncSession,
        user_id: str,
        quest_type: str,
        target: int,
        reward_type: str,
        reward_value: str,
        expires_days: int | None = None,
    ) -> LoyaltyQuest:
        quest = LoyaltyQuest(
            user_id=user_id,
            quest_type=quest_type,
            target=target,
            reward_type=reward_type,
            reward_value=reward_value,
            expires_at=(datetime.utcnow() + timedelta(days=expires_days)) if expires_days else None,
        )
        db.add(quest)
        await db.flush()
        return quest

    async def ensure_default_quests(self, db: AsyncSession, user_id: str) -> None:
        """Create default quests for a new user if none exist."""
        result = await db.execute(select(LoyaltyQuest).where(LoyaltyQuest.user_id == user_id))
        if result.scalars().first():
            return
        defaults = [
            ("purchase_count", 3, "points", "500", 90),
            ("review_writer", 2, "discount", "10%", 60),
            ("category_explorer", 2, "free_shipping", "free", 60),
        ]
        for quest_type, target, reward_type, reward_value, expires_days in defaults:
            await self.create_quest(
                db, user_id, quest_type, target, reward_type, reward_value, expires_days
            )

    async def record_event(
        self,
        db: AsyncSession,
        user_id: str,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[LoyaltyQuest]:
        """Update quest progress based on a user event."""
        await self.ensure_default_quests(db, user_id)
        quests = await self.get_active_quests(db, user_id)
        completed: list[LoyaltyQuest] = []
        for quest in quests:
            if quest.quest_type == "purchase_count" and event_type == "order_placed":
                quest.progress += 1
            elif quest.quest_type == "review_writer" and event_type == "review_created":
                quest.progress += 1
            elif (
                quest.quest_type == "category_explorer"
                and event_type == "order_placed"
                and metadata
            ):
                # Track distinct categories purchased in this quest's lifetime.
                # For simplicity, increment once per order containing a new category.
                category_id = metadata.get("category_id")
                if category_id:
                    quest.progress = min(quest.target, quest.progress + 1)

            if quest.progress >= quest.target and quest.completed_at is None:
                quest.completed_at = datetime.utcnow()
                completed.append(quest)
        await db.flush()
        return completed

    async def generate_birthday_campaign(
        self, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Find users with birthdays this week and generate offers."""
        today = datetime.utcnow().date()
        # Users whose birthday (month/day) falls in the next 7 days.
        result = await db.execute(
            select(User).where(
                func.strftime("%m-%d", User.birthday) >= today.strftime("%m-%d")
            ).where(
                func.strftime("%m-%d", User.birthday) <= (today + timedelta(days=7)).strftime("%m-%d")
            )
        )
        users = result.scalars().all()

        offers = []
        for user in users:
            offer = {
                "user_id": str(user.id),
                "email": user.email,
                "birthday": user.birthday.isoformat() if user.birthday else None,
                "offer_type": "discount",
                "discount_percent": 15,
                "message": f"¡Feliz cumpleaños{(', ' + user.name) if user.name else ''}! Disfruta 15% de descuento en tu próxima compra.",
            }
            offers.append(offer)
        return offers

    async def get_loyalty_insights(
        self, db: AsyncSession, user_id: str
    ) -> dict[str, Any]:
        status = await loyalty_service.get_user_loyalty(db, UUID(user_id))
        risk = await self.predict_churn_risk(db, user_id)
        offer = await self.suggest_retention_offer(db, user_id)
        await self.ensure_default_quests(db, user_id)
        quests = await self.get_active_quests(db, user_id)
        return {
            "status": status,
            "churn_risk": risk,
            "retention_offer": offer,
            "active_quests": [
                {
                    "id": str(q.id),
                    "quest_type": q.quest_type,
                    "progress": q.progress,
                    "target": q.target,
                    "reward_type": q.reward_type,
                    "reward_value": q.reward_value,
                    "expires_at": q.expires_at.isoformat() if q.expires_at else None,
                }
                for q in quests
            ],
        }


ai_loyalty_service = AILoyaltyService()
