from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.services.promotion_service import promotion_service
from app.dependencies import get_current_user_optional

router = APIRouter(prefix="/promotions", tags=["promotions"])


@router.get("/")
async def list_promotions(db: AsyncSession = Depends(get_db)):
    return await promotion_service.get_promotions(db)


@router.post("/apply")
async def apply_coupon(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user_optional(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # TODO: Get order total from cart/session
    order_total = 100.0  # Placeholder

    result = await promotion_service.apply_coupon(db, code, user.id, order_total)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
