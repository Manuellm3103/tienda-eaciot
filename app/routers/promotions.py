from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.services.promotion_service import promotion_service

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get("/")
async def list_promotions(db: AsyncSession = Depends(get_db)):
    return await promotion_service.get_promotions(db)


@router.post("/apply")
async def apply_coupon(code: str, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # TODO: Get order total from cart/session
    order_total = 100.0  # Placeholder
    
    result = await promotion_service.apply_coupon(db, code, UUID(user_id), order_total)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result
