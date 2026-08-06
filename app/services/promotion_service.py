from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from app.models.promotion import Promotion, Coupon
from app.models.congratulation import CongratulationRule, CongratulationHistory
from app.models.user import User
from app.schemas.promotion import PromotionCreate, CongratulationRuleCreate
import secrets


class PromotionService:
    async def create_promotion(self, db: AsyncSession, data: PromotionCreate) -> Promotion:
        promotion = Promotion(**data.model_dump())
        db.add(promotion)
        await db.flush()
        return promotion
    
    async def get_promotions(self, db: AsyncSession, active_only: bool = True) -> List[Promotion]:
        query = select(Promotion)
        if active_only:
            query = query.where(Promotion.is_active == True, Promotion.is_approved == True)
        result = await db.execute(query.order_by(Promotion.created_at.desc()))
        return result.scalars().all()
    
    async def approve_promotion(self, db: AsyncSession, promotion_id: UUID) -> Optional[Promotion]:
        result = await db.execute(select(Promotion).where(Promotion.id == promotion_id))
        promotion = result.scalar_one_or_none()
        if not promotion:
            return None
        promotion.is_approved = True
        await db.flush()
        return promotion
    
    async def apply_coupon(self, db: AsyncSession, code: str, user_id: UUID, order_total: float) -> dict:
        result = await db.execute(select(Coupon).where(Coupon.code == code, Coupon.is_used == False))
        coupon = result.scalar_one_or_none()
        
        if not coupon:
            return {"valid": False, "error": "Coupon not found or already used"}
        
        if coupon.user_id and coupon.user_id != user_id:
            return {"valid": False, "error": "Coupon not valid for this user"}
        
        if coupon.expires_at and coupon.expires_at < datetime.utcnow():
            return {"valid": False, "error": "Coupon expired"}
        
        # Get promotion details
        promo = await db.get(Promotion, coupon.promotion_id)
        if not promo or not promo.is_active:
            return {"valid": False, "error": "Promotion no longer active"}
        
        # Calculate discount
        if promo.discount_type == "percentage":
            discount = order_total * (float(promo.discount_value) / 100)
        elif promo.discount_type == "fixed":
            discount = min(float(promo.discount_value), order_total)
        else:
            discount = 0
        
        return {
            "valid": True,
            "discount": discount,
            "coupon_id": str(coupon.id),
            "promotion_id": str(promo.id),
        }
    
    async def create_congratulation_rule(self, db: AsyncSession, data: CongratulationRuleCreate) -> CongratulationRule:
        rule = CongratulationRule(**data.model_dump())
        db.add(rule)
        await db.flush()
        return rule
    
    async def get_congratulation_rules(self, db: AsyncSession) -> List[CongratulationRule]:
        result = await db.execute(
            select(CongratulationRule).where(CongratulationRule.is_active == True)
        )
        return result.scalars().all()
    
    async def check_congratulation_rules(self, db: AsyncSession, user: User, order_id: UUID) -> List[dict]:
        triggered = []
        rules = await self.get_congratulation_rules(db)
        
        for rule in rules:
            should_trigger = False
            
            if rule.event_type == "total_spent" and float(user.total_spent) >= float(rule.event_value):
                should_trigger = True
            elif rule.event_type == "purchase_count" and user.purchase_count >= int(rule.event_value):
                should_trigger = True
            elif rule.event_type == "loyalty_level_up" and user.loyalty_level == rule.event_value:
                should_trigger = True
            
            if should_trigger:
                triggered.append({
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "message": rule.message_template,
                    "reward_type": rule.reward_type,
                    "reward_value": float(rule.reward_value) if rule.reward_value else None,
                })
                
                # Record history
                history = CongratulationHistory(
                    user_id=user.id,
                    rule_id=rule.id,
                    order_id=order_id,
                    message_sent=rule.message_template,
                    reward_sent=f"{rule.reward_type}: {rule.reward_value}",
                )
                db.add(history)
                rule.current_uses += 1
        
        await db.flush()
        return triggered


promotion_service = PromotionService()
