from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.dynamic_pricing import dynamic_pricing
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/pricing",
    tags=["admin-pricing"],
    dependencies=[Depends(require_admin)],
)


class ApplyPriceRequest(BaseModel):
    product_id: str = Field(min_length=1)
    new_price: float = Field(gt=0)


class SimulateRequest(BaseModel):
    product_id: str = Field(min_length=1)
    multiplier: float = Field(gt=0)


class ToggleRequest(BaseModel):
    product_id: str = Field(min_length=1)
    enabled: bool


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


@router.post("/apply")
async def apply_price(
    request: Request,
    data: ApplyPriceRequest,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    try:
        product = await dynamic_pricing.apply_recommendation(
            db, data.product_id, data.new_price
        )
        await db.commit()
        return JSONResponse(
            {
                "product_id": str(product.id),
                "new_price": float(product.price),
                "price_updated_at": (
                    product.price_updated_at.isoformat()
                    if product.price_updated_at
                    else None
                ),
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/simulate")
async def simulate_price(
    request: Request,
    data: SimulateRequest,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    try:
        result = await dynamic_pricing.simulate_price(
            db, data.product_id, data.multiplier
        )
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/toggle")
async def toggle_auto_apply(
    request: Request,
    data: ToggleRequest,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    try:
        product = await dynamic_pricing.toggle_auto_apply(
            db, data.product_id, data.enabled
        )
        await db.commit()
        return JSONResponse(
            {
                "product_id": str(product.id),
                "dynamic_pricing_enabled": bool(product.dynamic_pricing_enabled),
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/refresh-analytics")
async def refresh_analytics(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    count = await dynamic_pricing.refresh_product_analytics(db)
    await db.commit()
    return JSONResponse({"refreshed": count})
