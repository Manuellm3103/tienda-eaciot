from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_dashboard_metrics(db)


@router.get("/ai/suggestions")
async def get_ai_suggestions(db: AsyncSession = Depends(get_db)):
    return await dashboard_service.get_ai_suggestions(db)


@router.post("/ai/suggestions/approve")
async def approve_suggestion(
    suggestion_type: str, 
    suggestion_data: dict,
    db: AsyncSession = Depends(get_db)
):
    return await dashboard_service.approve_suggestion(db, suggestion_type, suggestion_data)
