from pydantic import BaseModel
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ShippingAddressCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    street: str
    number: Optional[str] = None
    apartment: Optional[str] = None
    neighborhood: Optional[str] = None
    city: str
    state: str
    zip_code: str
    country: str = "México"
    is_default: bool = False


class ShippingAddressResponse(BaseModel):
    id: UUID
    name: str
    phone: Optional[str]
    street: str
    number: Optional[str]
    apartment: Optional[str]
    neighborhood: Optional[str]
    city: str
    state: str
    zip_code: str
    country: str
    is_default: str
    
    class Config:
        from_attributes = True


class ShipmentCreate(BaseModel):
    order_id: UUID
    carrier: str
    tracking_number: Optional[str] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[Dict] = None
    shipping_cost: Decimal


class ShipmentResponse(BaseModel):
    id: UUID
    order_id: UUID
    carrier: str
    tracking_number: Optional[str]
    tracking_url: Optional[str]
    status: str
    estimated_delivery: Optional[datetime]
    delivered_at: Optional[datetime]
    shipping_cost: Optional[Decimal]
    created_at: datetime
    
    class Config:
        from_attributes = True
