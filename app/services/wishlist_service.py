from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from uuid import UUID
from app.models.wishlist import Wishlist
from app.models.product import Product


class WishlistService:
    async def add_to_wishlist(self, db: AsyncSession, user_id: UUID, product_id: UUID) -> bool:
        """Add product to wishlist"""
        # Check if already in wishlist
        result = await db.execute(
            select(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id == product_id,
            )
        )
        if result.scalar_one_or_none():
            return False  # Already in wishlist
        
        wishlist_item = Wishlist(user_id=user_id, product_id=product_id)
        db.add(wishlist_item)
        await db.flush()
        return True
    
    async def remove_from_wishlist(self, db: AsyncSession, user_id: UUID, product_id: UUID) -> bool:
        """Remove product from wishlist"""
        result = await db.execute(
            delete(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id == product_id,
            )
        )
        await db.flush()
        return result.rowcount > 0
    
    async def get_wishlist(self, db: AsyncSession, user_id: UUID) -> List[Product]:
        """Get all products in wishlist"""
        result = await db.execute(
            select(Product)
            .join(Wishlist, Wishlist.product_id == Product.id)
            .where(Wishlist.user_id == user_id, Product.is_active == True)
            .order_by(Wishlist.created_at.desc())
        )
        return result.scalars().all()
    
    async def is_in_wishlist(self, db: AsyncSession, user_id: UUID, product_id: UUID) -> bool:
        """Check if product is in wishlist"""
        result = await db.execute(
            select(Wishlist).where(
                Wishlist.user_id == user_id,
                Wishlist.product_id == product_id,
            )
        )
        return result.scalar_one_or_none() is not None


wishlist_service = WishlistService()
