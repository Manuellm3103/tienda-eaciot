from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from app.database import get_db
from app.schemas.product import ProductResponse, CategoryResponse
from app.services.product_service import product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/", response_model=List[ProductResponse])
async def list_products(category_id: Optional[UUID] = None, db: AsyncSession = Depends(get_db)):
    return await product_service.get_products(db, category_id)


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/categories/", response_model=List[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await product_service.get_categories(db)
