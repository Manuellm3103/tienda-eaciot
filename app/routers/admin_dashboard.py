from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    metrics = await dashboard_service.get_dashboard_metrics(db)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "metrics": metrics},
    )


@router.get("/dashboard/data")
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
