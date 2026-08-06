from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, CategoryCreate, CategoryResponse
from app.services.product_service import product_service

router = APIRouter(prefix="/admin/products", tags=["admin-products"])


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
