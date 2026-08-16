from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import require_admin, get_current_user_optional
from app.models.user import User
from app.models.product_bundle import ProductBundle
from app.models.product import Product
from app.schemas.product import ProductResponse
from app.services.bundle_service import bundle_service
from app.middleware import validate_csrf
from app.templates_instance import templates
from sqlalchemy import select

router = APIRouter(prefix="/bundles", tags=["bundles"])


@router.get("/product/{product_id}")
async def bundles_for_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return bundles that include the given product."""
    bundles = await bundle_service.get_bundles_for_product(db, str(product_id))
    output = []
    for bundle in bundles:
        pricing = await bundle_service.calculate_bundle_price(db, bundle)
        output.append({
            "id": bundle.id,
            "name": bundle.name,
            "product_ids": bundle.product_ids,
            "discount_type": bundle.discount_type,
            "discount_value": float(bundle.discount_value),
            "original_price": pricing["original_price"],
            "final_price": pricing["final_price"],
            "score": float(bundle.score) if bundle.score else None,
        })
    return output


@router.post("/admin/generate")
async def generate_bundles(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin endpoint to mine order history and generate AI bundles."""
    await validate_csrf(request)
    bundles = await bundle_service.generate_bundles(db, min_support=1)
    await db.commit()
    return {"created": len(bundles)}


@router.get("/admin", response_class=HTMLResponse)
async def bundles_admin_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Render the AI bundles management page."""
    result = await db.execute(
        select(ProductBundle).order_by(ProductBundle.created_at.desc())
    )
    bundles = result.scalars().all()
    enriched = []
    for bundle in bundles:
        pricing = await bundle_service.calculate_bundle_price(db, bundle)
        prod_result = await db.execute(
            select(Product.id, Product.title)
            .where(Product.id.in_(bundle.product_ids))
        )
        names = {row.id: row.title for row in prod_result.all()}
        enriched.append({
            "bundle": bundle,
            "names": [names.get(pid, "?") for pid in bundle.product_ids],
            "pricing": pricing,
        })
    return templates.TemplateResponse(
        "admin/bundles.html",
        {"request": request, "bundles": enriched},
    )


@router.post("/admin/{bundle_id}/toggle")
async def toggle_bundle(
    bundle_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await validate_csrf(request)
    result = await db.execute(select(ProductBundle).where(ProductBundle.id == str(bundle_id)))
    bundle = result.scalar_one_or_none()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    bundle.is_active = not bundle.is_active
    await db.commit()
    return {"is_active": bundle.is_active}
