"""Product variant CRUD (#10)."""
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product_variant import ProductVariant


class VariantService:
    async def list_variants(self, db: AsyncSession, product_id: str) -> List[ProductVariant]:
        result = await db.execute(
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.created_at.asc())
        )
        return result.scalars().all()

    async def get_variant(self, db: AsyncSession, variant_id: str) -> Optional[ProductVariant]:
        return await db.get(ProductVariant, variant_id)

    async def create_variant(
        self,
        db: AsyncSession,
        product_id: str,
        name: str,
        price_delta: Decimal = Decimal("0"),
        stock: int = -1,
        sku: Optional[str] = None,
    ) -> ProductVariant:
        variant = ProductVariant(
            product_id=product_id,
            name=name,
            sku=sku or None,
            price_delta=price_delta,
            stock=stock,
        )
        db.add(variant)
        await db.flush()
        return variant

    async def update_variant(
        self,
        db: AsyncSession,
        variant_id: str,
        *,
        name: Optional[str] = None,
        price_delta: Optional[Decimal] = None,
        stock: Optional[int] = None,
        sku: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[ProductVariant]:
        variant = await self.get_variant(db, variant_id)
        if not variant:
            return None
        if name is not None:
            variant.name = name
        if price_delta is not None:
            variant.price_delta = price_delta
        if stock is not None:
            variant.stock = stock
        if sku is not None:
            variant.sku = sku or None
        if is_active is not None:
            variant.is_active = is_active
        await db.flush()
        return variant

    async def delete_variant(self, db: AsyncSession, variant_id: str) -> bool:
        variant = await self.get_variant(db, variant_id)
        if not variant:
            return False
        await db.delete(variant)
        await db.flush()
        return True


variant_service = VariantService()
