from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, CategoryCreate, CategoryResponse
from app.services.product_service import product_service
from app.services.product_content_service import product_content_service
from app.middleware import validate_csrf
from app.dependencies import require_admin

router = APIRouter(
    prefix="/admin/products",
    tags=["admin-products"],
    dependencies=[Depends(require_admin)],
)
from app.templates_instance import templates


@router.post("/", response_model=ProductResponse)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    return await product_service.create_product(db, data)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: UUID, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    product = await product_service.update_product(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.delete("/{product_id}")
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    success = await product_service.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}


@router.post("/categories/", response_model=CategoryResponse)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    return await product_service.create_category(db, data)


@router.post("/batch-enrich")
async def admin_products_batch_enrich(
    request: Request,
    db: AsyncSession = Depends(get_db),
    force: bool = Query(False),
):
    """Generate AI content for products.

    force=false: solo los que tienen descripción corta o vacía.
    force=true: reescribe TODOS los productos activos.
    """
    await validate_csrf(request)
    result = await product_content_service.batch_enrich(db, force=force)
    await db.commit()
    return JSONResponse(result)


@router.post("/{product_id}/generate-content")
async def admin_product_generate_content(
    request: Request,
    product_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate + persist SEO content for a single product."""
    await validate_csrf(request)
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    result = await product_content_service.apply_to_product(db, product)
    await db.commit()
    response_payload = {
        "product_id": product_id,
        "status": result["status"],
    }
    if "content_score" in result:
        response_payload["content_score"] = result["content_score"]
    if "seo_score" in result:
        response_payload["seo_score"] = result["seo_score"]
    return JSONResponse(response_payload)


# ==================== HTML ADMIN PAGES ====================


def _parse_specs(text: str) -> Optional[dict]:
    """Parse 'Clave: Valor' lines into a specs dict. Empty -> None."""
    specs = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if key and value:
            specs[key] = value
    return specs or None


def _normalize_video(url: str) -> str:
    """Convert a YouTube watch/short URL into an embeddable URL."""
    url = url.strip()
    if "youtu.be/" in url:
        vid = url.rsplit("youtu.be/", 1)[1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/embed/{vid}"
    if "watch?v=" in url:
        vid = url.rsplit("watch?v=", 1)[1].split("&")[0]
        return f"https://www.youtube.com/embed/{vid}"
    if "youtube.com/shorts/" in url:
        vid = url.rsplit("/shorts/", 1)[1].split("?")[0].split("/")[0]
        return f"https://www.youtube.com/embed/{vid}"
    return url


def _parse_videos(text: str) -> Optional[list]:
    """Parse one-URL-per-line into a normalized embed URL list."""
    vids = [_normalize_video(line) for line in (text or "").splitlines() if line.strip()]
    return vids or None

@router.get("/", response_class=HTMLResponse)
async def admin_products_list(request: Request, db: AsyncSession = Depends(get_db)):
    products = await product_service.get_products(db, active_only=False)
    categories = await product_service.get_categories(db)
    return templates.TemplateResponse(
        "admin/products.html",
        {"request": request, "products": products, "categories": categories},
    )


@router.get("/new", response_class=HTMLResponse)
async def admin_product_new(request: Request, db: AsyncSession = Depends(get_db)):
    categories = await product_service.get_categories(db)
    return templates.TemplateResponse(
        "admin/product_form.html",
        {"request": request, "categories": categories, "product": None},
    )


@router.post("/new")
async def admin_product_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form(...),
    product_type: str = Form(...),
    category_id: str = Form(""),
    stock: int = Form(100),
    image_url: str = Form(""),
    specs: str = Form(""),
    videos: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    data = ProductCreate(
        title=title,
        description=description or None,
        price=Decimal(price),
        product_type=product_type,
        category_id=category_id or None,
        stock=stock,
        image_url=image_url or None,
        specs=_parse_specs(specs),
        videos=_parse_videos(videos),
    )
    await product_service.create_product(db, data)
    await db.commit()
    return RedirectResponse(url="/admin/products/", status_code=302)


@router.get("/{product_id}/edit", response_class=HTMLResponse)
async def admin_product_edit(request: Request, product_id: str, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    categories = await product_service.get_categories(db)
    return templates.TemplateResponse(
        "admin/product_form.html",
        {"request": request, "product": product, "categories": categories},
    )


@router.post("/{product_id}/edit")
async def admin_product_update(
    request: Request,
    product_id: str,
    title: str = Form(...),
    description: str = Form(""),
    price: str = Form(...),
    product_type: str = Form(...),
    category_id: str = Form(""),
    stock: int = Form(100),
    image_url: str = Form(""),
    specs: str = Form(""),
    videos: str = Form(""),
    is_active: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    data = ProductUpdate(
        title=title,
        description=description or None,
        price=Decimal(price),
        product_type=product_type,
        category_id=category_id or None,
        stock=stock,
        image_url=image_url or None,
        specs=_parse_specs(specs),
        videos=_parse_videos(videos),
        is_active=is_active,
    )
    await product_service.update_product(db, product_id, data)
    await db.commit()
    return RedirectResponse(url="/admin/products/", status_code=302)


@router.post("/{product_id}/delete")
async def admin_product_delete(request: Request, product_id: str, db: AsyncSession = Depends(get_db)):
    await validate_csrf(request)
    await product_service.delete_product(db, product_id)
    await db.commit()
    return RedirectResponse(url="/admin/products/", status_code=302)
