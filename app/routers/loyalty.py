from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.services.loyalty_service import loyalty_service

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


@router.get("/status")
async def get_loyalty_status(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        return await loyalty_service.get_user_loyalty(db, UUID(user_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history")
async def get_loyalty_history(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await loyalty_service.get_loyalty_history(db, UUID(user_id))
