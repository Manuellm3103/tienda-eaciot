from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.variant_service import variant_service

router = APIRouter(
    prefix="/admin/products",
    tags=["admin-variants"],
    dependencies=[Depends(require_admin)],
)


@router.get("/{product_id}/variants")
async def list_variants(product_id: str, db: AsyncSession = Depends(get_db)):
    variants = await variant_service.list_variants(db, product_id)
    return JSONResponse(
        {
            "variants": [
                {
                    "id": str(v.id),
                    "name": v.name,
                    "sku": v.sku,
                    "price_delta": float(v.price_delta or 0),
                    "stock": v.stock,
                    "is_active": v.is_active,
                }
                for v in variants
            ]
        }
    )


@router.post("/{product_id}/variants")
async def create_variant(
    product_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    body = await request.json()
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name requerido")
    variant = await variant_service.create_variant(
        db,
        product_id,
        name=name,
        price_delta=Decimal(str(body.get("price_delta") or 0)),
        stock=int(body.get("stock") or -1),
        sku=(body.get("sku") or "").strip() or None,
    )
    await db.commit()
    return JSONResponse({"id": str(variant.id), "name": variant.name})


@router.post("/{product_id}/variants/{variant_id}")
async def update_variant(
    product_id: str,
    variant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    body = await request.json()
    kwargs = {}
    if "name" in body:
        kwargs["name"] = (body["name"] or "").strip()
    if "price_delta" in body:
        kwargs["price_delta"] = Decimal(str(body["price_delta"]))
    if "stock" in body:
        kwargs["stock"] = int(body["stock"])
    if "sku" in body:
        kwargs["sku"] = (body["sku"] or "").strip() or None
    if "is_active" in body:
        kwargs["is_active"] = bool(body["is_active"])
    variant = await variant_service.update_variant(db, variant_id, **kwargs)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    await db.commit()
    return JSONResponse({"id": str(variant.id)})


@router.delete("/{product_id}/variants/{variant_id}")
async def delete_variant(
    product_id: str,
    variant_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    deleted = await variant_service.delete_variant(db, variant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Variant not found")
    await db.commit()
    return JSONResponse({"message": "Variant deleted"})
