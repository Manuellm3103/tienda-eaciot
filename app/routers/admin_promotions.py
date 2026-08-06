from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.database import get_db
from app.schemas.promotion import PromotionCreate, PromotionResponse, CongratulationRuleCreate, CongratulationRuleResponse
from app.services.promotion_service import promotion_service

router = APIRouter(prefix="/admin/promotions", tags=["admin-promotions"])


@router.post("/", response_model=PromotionResponse)
async def create_promotion(data: PromotionCreate, db: AsyncSession = Depends(get_db)):
    return await promotion_service.create_promotion(db, data)


@router.post("/{promotion_id}/approve", response_model=PromotionResponse)
async def approve_promotion(promotion_id: UUID, db: AsyncSession = Depends(get_db)):
    promotion = await promotion_service.approve_promotion(db, promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return promotion


@router.post("/congratulations/rules/", response_model=CongratulationRuleResponse)
async def create_congratulation_rule(data: CongratulationRuleCreate, db: AsyncSession = Depends(get_db)):
    return await promotion_service.create_congratulation_rule(db, data)


@router.get("/congratulations/rules/")
async def list_congratulation_rules(db: AsyncSession = Depends(get_db)):
    return await promotion_service.get_congratulation_rules(db)
