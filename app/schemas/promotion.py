from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from datetime import datetime


class PromotionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    discount_type: str  # percentage, fixed, free_shipping
    discount_value: Decimal
    conditions: Optional[dict] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    coupon_code: Optional[str] = None


class PromotionResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    discount_type: str
    discount_value: Decimal
    is_active: bool
    is_approved: bool
    usage_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CongratulationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    event_type: str  # total_spent, purchase_count, specific_product, loyalty_level_up
    event_value: Optional[Decimal] = None
    event_product_id: Optional[UUID] = None
    reward_type: str  # coupon, free_product, points, free_shipping
    reward_value: Optional[Decimal] = None
    reward_product_id: Optional[UUID] = None
    message_template: str
    email_subject: Optional[str] = None


class CongratulationRuleResponse(BaseModel):
    id: UUID
    name: str
    event_type: str
    reward_type: str
    is_active: bool
    current_uses: int
    created_at: datetime
    
    class Config:
        from_attributes = True
