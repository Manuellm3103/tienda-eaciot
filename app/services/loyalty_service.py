from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from uuid import UUID
from decimal import Decimal
from app.models.user import User
from app.models.loyalty import LoyaltyHistory


class LoyaltyService:
    LEVELS = {
        "bronce": {"min": 0, "max": 499, "discount": 5},
        "plata": {"min": 500, "max": 1499, "discount": 10},
        "oro": {"min": 1500, "max": 4999, "discount": 15},
        "diamante": {"min": 5000, "max": float("inf"), "discount": 20},
    }
    
    def calculate_level(self, total_spent: Decimal) -> str:
        spent = float(total_spent)
        if spent >= 5000:
            return "diamante"
        elif spent >= 1500:
            return "oro"
        elif spent >= 500:
            return "plata"
        return "bronce"
    
    def get_discount(self, level: str) -> int:
        return self.LEVELS.get(level, {}).get("discount", 0)
    
    async def update_user_loyalty(
        self, db: AsyncSession, user_id: UUID, order_total: Decimal, order_id: UUID
    ) -> dict:
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        old_level = user.loyalty_level
        user.total_spent += order_total
        user.purchase_count += 1
        user.loyalty_points += int(order_total)
        user.last_purchase_at = func.now()
        
        new_level = self.calculate_level(user.total_spent)
        user.loyalty_level = new_level
        
        # Record history
        history = LoyaltyHistory(
            user_id=user_id,
            points_change=int(order_total),
            reason=f"Purchase order #{str(order_id)[:8]}",
            order_id=order_id,
        )
        db.add(history)
        
        await db.flush()
        
        return {
            "old_level": old_level,
            "new_level": new_level,
            "level_up": old_level != new_level,
            "points_earned": int(order_total),
            "total_points": user.loyalty_points,
        }
    
    async def get_user_loyalty(self, db: AsyncSession, user_id: UUID) -> dict:
        user = await db.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        
        return {
            "level": user.loyalty_level,
            "points": user.loyalty_points,
            "total_spent": float(user.total_spent),
            "purchase_count": user.purchase_count,
            "discount": self.get_discount(user.loyalty_level),
            "next_level": self._get_next_level(user.loyalty_level),
            "points_to_next": self._get_points_to_next(user.loyalty_level, user.total_spent),
        }
    
    def _get_next_level(self, current: str) -> str:
        levels = ["bronce", "plata", "oro", "diamante"]
        idx = levels.index(current)
        return levels[min(idx + 1, len(levels) - 1)]
    
    def _get_points_to_next(self, current: str, total_spent: Decimal) -> int:
        thresholds = {"bronce": 500, "plata": 1500, "oro": 5000}
        next_threshold = thresholds.get(current)
        if not next_threshold:
            return 0
        return max(0, next_threshold - int(total_spent))
    
    async def get_loyalty_history(self, db: AsyncSession, user_id: UUID) -> List[LoyaltyHistory]:
        result = await db.execute(
            select(LoyaltyHistory)
            .where(LoyaltyHistory.user_id == user_id)
            .order_by(LoyaltyHistory.created_at.desc())
        )
        return result.scalars().all()


loyalty_service = LoyaltyService()
