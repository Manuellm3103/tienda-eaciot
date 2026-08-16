from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.product import Product
from app.models.user import User
from app.services.inventory_forecast import inventory_forecaster
from app.templates_instance import templates


router = APIRouter(prefix="/admin/inventory", tags=["admin-inventory"])


@router.get("/")
async def inventory_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    products = await inventory_forecaster.get_low_stock_products(db)
    return templates.TemplateResponse(
        "admin/inventory.html",
        {"request": request, "products": products},
    )


@router.get("/forecast/{product_id}")
async def product_forecast(
    product_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    prediction = await inventory_forecaster.predict_stockout(db, product_id)
    return JSONResponse(prediction)
