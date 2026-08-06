from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse)
async def create_order(data: OrderCreate, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        return await order_service.create_order(db, UUID(user_id), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[OrderResponse])
async def list_orders(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await order_service.get_user_orders(db, UUID(user_id))


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    order = await order_service.get_order(db, order_id)
    if not order or str(order.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order
