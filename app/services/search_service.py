from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from uuid import UUID
from app.models.product import Product, Category
from app.ai.llm_router import llm_router, TaskType


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
        extra_terms: Optional[List[str]] = None,
    ) -> dict:
        """Search products with filters"""
        # Build query
        stmt = select(Product).where(Product.is_active == True)

        # Text search (simple LIKE - for production use full-text search)
        if query or extra_terms:
            conditions = []
            if query:
                t = f"%{query}%"
                conditions.append(or_(Product.title.ilike(t), Product.description.ilike(t)))
            for term in (extra_terms or []):
                t = f"%{term}%"
                conditions.append(or_(Product.title.ilike(t), Product.description.ilike(t)))
            stmt = stmt.where(or_(*conditions))

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
    
    async def expand_query(self, query: str, limit: int = 4) -> List[str]:
        """Ask the LLM for alternative Spanish search terms for a dead query."""
        if not query:
            return []
        prompt = (
            f"Genera {limit} términos de búsqueda alternativos en español para "
            f"'{query}' (sinónimos, palabras relacionadas o correcciones de tipeo). "
            'Responde SOLO en JSON: {"terms": ["...", "..."]}'
        )
        data = await llm_router.generate_structured(
            prompt,
            system="Eres un motor de búsqueda de e-commerce.",
            task_type=TaskType.CLASSIFICATION,
        )
        terms = [
            t.strip()
            for t in data.get("terms", [])
            if t and t.strip().lower() != query.lower()
        ]
        return terms[:limit]

    async def search_with_expansion(
        self,
        db: AsyncSession,
        query: str,
        category_id: Optional[UUID] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        product_type: Optional[str] = None,
        sort_by: str = "relevance",
        per_page: int = 20,
    ) -> dict:
        """Exact search first; on zero hits, fall back to AI-expanded terms."""
        result = await self.search_products(
            db,
            query,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            product_type=product_type,
            sort_by=sort_by,
            per_page=per_page,
        )
        result["ai_expanded"] = False
        result["expanded_terms"] = []
        if result["total"] > 0:
            return result

        terms = await self.expand_query(query)
        if not terms:
            return result

        expanded = await self.search_products(
            db,
            "",
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            product_type=product_type,
            sort_by=sort_by,
            per_page=per_page,
            extra_terms=terms,
        )
        expanded["ai_expanded"] = True
        expanded["expanded_terms"] = terms
        return expanded

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
