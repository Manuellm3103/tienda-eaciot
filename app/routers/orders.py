from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.schemas.order import OrderCreate, OrderResponse
from app.services.order_service import order_service
from app.services.fraud_detector import fraud_detector
from app.services.auth_service import decode_token

router = APIRouter(prefix="/orders", tags=["orders"])


async def _get_user_id(request: Request, db: AsyncSession) -> str:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id


@router.post("/", response_model=OrderResponse)
async def create_order(data: OrderCreate, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = await _get_user_id(request, db)
    try:
        order = await order_service.create_order(db, user_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Best-effort fraud scoring; never blocks fulfillment.
    client_ip = request.client.host if request.client else None
    try:
        await fraud_detector.score_order(db, order, client_ip=client_ip)
    except Exception:
        # Fraud scoring failure must not break the order flow.
        pass

    return order


@router.get("/", response_model=List[OrderResponse])
async def list_orders(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = await _get_user_id(request, db)
    return await order_service.get_user_orders(db, user_id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = await _get_user_id(request, db)
    order = await order_service.get_order(db, order_id)
    if not order or str(order.user_id) != str(user_id):
        raise HTTPException(status_code=404, detail="Order not found")
    return order
