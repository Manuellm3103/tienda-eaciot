from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.schemas.shipping import ShippingAddressCreate, ShippingAddressResponse, ShipmentResponse
from app.services.shipping_service import shipping_service
from app.dependencies import get_current_user

router = APIRouter(prefix="/shipping", tags=["shipping"])


@router.post("/addresses", response_model=ShippingAddressResponse)
async def create_address(
    data: ShippingAddressCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await shipping_service.create_address(db, user.id, data)


@router.get("/addresses", response_model=List[ShippingAddressResponse])
async def get_addresses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await shipping_service.get_user_addresses(db, user.id)


@router.get("/addresses/{address_id}", response_model=ShippingAddressResponse)
async def get_address(
    address_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    address = await shipping_service.get_address(db, address_id)
    if not address or str(address.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Address not found")
    return address


@router.get("/calculate")
async def calculate_shipping(
    weight: float,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    """Calculate shipping cost"""
    from decimal import Decimal
    cost = shipping_service.calculate_shipping_cost(Decimal(str(weight)), state)
    return {"cost": float(cost), "state": state}


@router.get("/order/{order_id}", response_model=ShipmentResponse)
async def get_order_shipment(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    shipment = await shipping_service.get_order_shipment(db, order_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment
