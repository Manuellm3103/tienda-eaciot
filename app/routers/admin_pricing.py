from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.services.dynamic_pricing import dynamic_pricing
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/pricing",
    tags=["admin-pricing"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def pricing_page(request: Request):
    return templates.TemplateResponse("admin/pricing.html", {"request": request})


@router.get("/recommendations")
async def pricing_recommendations(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    recommendations = await dynamic_pricing.get_recommendations(db)
    insights = await dynamic_pricing.get_insights(db)
    return JSONResponse({"insights": insights, "recommendations": recommendations})
