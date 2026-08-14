from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = 1
    variant_id: Optional[UUID] = None


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    coupon_code: Optional[str] = None
    shipping_address: Optional[dict] = None


class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    price_at_purchase: Decimal
    
    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: UUID
    user_id: UUID
    subtotal: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    total_amount: Decimal
    status: str
    payment_method: Optional[str]
    items: List[OrderItemResponse]
    created_at: datetime
    
    class Config:
        from_attributes = True
