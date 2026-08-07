from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class RefundCreate(BaseModel):
    order_id: UUID
    amount: Decimal
    reason: str
    refund_method: str = "original_payment"


class RefundResponse(BaseModel):
    id: UUID
    order_id: UUID
    user_id: UUID
    amount: Decimal
    reason: str
    status: str
    refund_method: str
    admin_notes: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
