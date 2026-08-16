from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class ReviewCreate(BaseModel):
    product_id: UUID
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: UUID
    user_id: UUID
    product_id: UUID
    rating: int
    title: Optional[str]
    comment: Optional[str]
    is_verified_purchase: bool
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    ai_response: Optional[str] = None
    ai_response_approved: bool = False
    ai_responded_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
