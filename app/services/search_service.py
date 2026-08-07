from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from uuid import UUID
from app.models.product import Product, Category


class SearchService:
    async def search_products(
        self,
        db: AsyncSession,
        query: str,
        category_id: Optional[UUID] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        product_type: Optional[str] = None,
        sort_by: str = "relevance",
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """Search products with filters"""
        # Build query
        stmt = select(Product).where(Product.is_active == True)
        
        # Text search (simple LIKE - for production use full-text search)
        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                or_(
                    Product.title.ilike(search_term),
                    Product.description.ilike(search_term),
                )
            )
        
        # Category filter
        if category_id:
            stmt = stmt.where(Product.category_id == category_id)
        
        # Price filters
        if min_price is not None:
            stmt = stmt.where(Product.price >= min_price)
        if max_price is not None:
            stmt = stmt.where(Product.price <= max_price)
        
        # Product type filter
        if product_type:
            stmt = stmt.where(Product.product_type == product_type)
        
        # Sorting
        if sort_by == "price_asc":
            stmt = stmt.order_by(Product.price.asc())
        elif sort_by == "price_desc":
            stmt = stmt.order_by(Product.price.desc())
        elif sort_by == "newest":
            stmt = stmt.order_by(Product.created_at.desc())
        elif sort_by == "name":
            stmt = stmt.order_by(Product.title.asc())
        else:  # relevance - by creation date
            stmt = stmt.order_by(Product.created_at.desc())
        
        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Paginate
        offset = (page - 1) * per_page
        stmt = stmt.offset(offset).limit(per_page)
        
        result = await db.execute(stmt)
        products = result.scalars().all()
        
        return {
            "products": products,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page,
        }
    
    async def get_suggestions(self, db: AsyncSession, query: str, limit: int = 5) -> List[str]:
        """Get search suggestions"""
        if not query or len(query) < 2:
            return []
        
        search_term = f"%{query}%"
        result = await db.execute(
            select(Product.title)
            .where(Product.is_active == True, Product.title.ilike(search_term))
            .limit(limit)
        )
        return [row[0] for row in result.all()]
    
    async def get_popular_searches(self, db: AsyncSession, limit: int = 10) -> List[str]:
        """Get popular search terms (simplified - returns category names)"""
        result = await db.execute(
            select(Category.name)
            .where(Category.is_active == True)
            .limit(limit)
        )
        return [row[0] for row in result.all()]


search_service = SearchService()
