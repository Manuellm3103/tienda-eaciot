from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from app.database import get_db
from app.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def search_products(
    q: str = Query(..., min_length=1),
    category: Optional[UUID] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    type: Optional[str] = None,
    sort: str = "relevance",
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Search products"""
    return await search_service.search_products(
        db=db,
        query=q,
        category_id=category,
        min_price=min_price,
        max_price=max_price,
        product_type=type,
        sort_by=sort,
        page=page,
        per_page=per_page,
    )


@router.get("/suggestions")
async def get_suggestions(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    """Get search suggestions"""
    return await search_service.get_suggestions(db, q)


@router.get("/popular")
async def get_popular_searches(db: AsyncSession = Depends(get_db)):
    """Get popular search terms"""
    return await search_service.get_popular_searches(db)
