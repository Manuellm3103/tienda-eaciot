from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from decimal import Decimal
from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, CategoryCreate, CategoryResponse
from app.services.product_service import product_service
from app.middleware import validate_csrf

router = APIRouter(prefix="/admin/products", tags=["admin-products"])
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


# ==================== HTML ADMIN PAGES ====================

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
