from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from app.models.product import Product, Category
from app.schemas.product import ProductCreate, ProductUpdate, CategoryCreate


class ProductService:
    async def get_products(
        self, db: AsyncSession, category_id: Optional[UUID] = None, active_only: bool = True
    ) -> List[Product]:
        query = select(Product)
        if active_only:
            query = query.where(Product.is_active == True)
        if category_id:
            query = query.where(Product.category_id == category_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_product(self, db: AsyncSession, product_id: UUID) -> Optional[Product]:
        result = await db.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()
    
    async def create_product(self, db: AsyncSession, data: ProductCreate) -> Product:
        payload = data.model_dump()
        # PKs/FKs are String(36); never bind a UUID object (SQLite rejects it).
        if payload.get("category_id"):
            payload["category_id"] = str(payload["category_id"])
        product = Product(**payload)
        db.add(product)
        await db.flush()
        return product

    async def update_product(self, db: AsyncSession, product_id: UUID, data: ProductUpdate) -> Optional[Product]:
        product = await self.get_product(db, product_id)
        if not product:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            if key == "category_id" and value:
                value = str(value)
            setattr(product, key, value)
        await db.flush()
        return product
    
    async def delete_product(self, db: AsyncSession, product_id: UUID) -> bool:
        product = await self.get_product(db, product_id)
        if not product:
            return False
        product.is_active = False
        await db.flush()
        return True
    
    async def get_categories(self, db: AsyncSession) -> List[Category]:
        result = await db.execute(select(Category).where(Category.is_active == True))
        return result.scalars().all()
    
    async def create_category(self, db: AsyncSession, data: CategoryCreate) -> Category:
        category = Category(**data.model_dump())
        db.add(category)
        await db.flush()
        return category


product_service = ProductService()
