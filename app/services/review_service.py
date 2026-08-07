from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from app.models.review import Review
from app.models.order import Order, OrderItem
from app.schemas.review import ReviewCreate


class ReviewService:
    async def create_review(self, db: AsyncSession, user_id: UUID, data: ReviewCreate) -> Review:
        """Create a product review"""
        # Check if user purchased this product
        is_verified = False
        result = await db.execute(
            select(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.user_id == user_id,
                OrderItem.product_id == data.product_id,
                Order.status.in_(["paid", "delivered"]),
            )
        )
        if result.scalar_one_or_none():
            is_verified = True
        
        review = Review(
            user_id=user_id,
            product_id=data.product_id,
            rating=data.rating,
            title=data.title,
            comment=data.comment,
            is_verified_purchase=is_verified,
        )
        db.add(review)
        await db.flush()
        return review
    
    async def get_product_reviews(self, db: AsyncSession, product_id: UUID) -> List[Review]:
        """Get all reviews for a product"""
        result = await db.execute(
            select(Review)
            .where(Review.product_id == product_id, Review.is_approved == True)
            .order_by(Review.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_product_rating(self, db: AsyncSession, product_id: UUID) -> dict:
        """Get average rating for a product"""
        result = await db.execute(
            select(
                func.avg(Review.rating).label("average"),
                func.count(Review.id).label("count"),
            )
            .where(Review.product_id == product_id, Review.is_approved == True)
        )
        row = result.one()
        return {
            "average": float(row.average) if row.average else 0,
            "count": row.count,
        }
    
    async def get_user_reviews(self, db: AsyncSession, user_id: UUID) -> List[Review]:
        """Get all reviews by a user"""
        result = await db.execute(
            select(Review)
            .where(Review.user_id == user_id)
            .order_by(Review.created_at.desc())
        )
        return result.scalars().all()
    
    async def delete_review(self, db: AsyncSession, review_id: UUID, user_id: UUID) -> bool:
        """Delete a review"""
        result = await db.execute(
            select(Review).where(Review.id == review_id, Review.user_id == user_id)
        )
        review = result.scalar_one_or_none()
        
        if not review:
            return False
        
        await db.delete(review)
        await db.flush()
        return True


review_service = ReviewService()
