from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Dict, List
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.promotion import Promotion
from app.ai.customer_analyzer import customer_analyzer
from app.ai.promotion_generator import promotion_generator
from app.ai.welcome_generator import welcome_generator


class DashboardService:
    async def get_dashboard_metrics(self, db: AsyncSession) -> dict:
        # Sales metrics
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        total_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(Order.status == "paid")
        )
        today_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(
                and_(Order.status == "paid", func.date(Order.created_at) == today)
            )
        )
        week_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(
                and_(Order.status == "paid", Order.created_at >= week_ago)
            )
        )
        
        # Customer metrics
        total_customers = await db.execute(select(func.count(User.id)))
        new_today = await db.execute(
            select(func.count(User.id)).where(func.date(User.created_at) == today)
        )
        
        # Loyalty distribution
        loyalty_dist = await db.execute(
            select(User.loyalty_level, func.count(User.id)).group_by(User.loyalty_level)
        )
        
        # Top products
        top_products = await db.execute(
            select(Product.title, func.sum(OrderItem.quantity).label("total_sold"))
            .join(OrderItem, Product.id == OrderItem.product_id)
            .group_by(Product.title)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
        )
        
        return {
            "sales": {
                "total": float(total_sales.scalar() or 0),
                "today": float(today_sales.scalar() or 0),
                "this_week": float(week_sales.scalar() or 0),
            },
            "customers": {
                "total": total_customers.scalar() or 0,
                "new_today": new_today.scalar() or 0,
                "loyalty_distribution": {row[0]: row[1] for row in loyalty_dist.all()},
            },
            "top_products": [
                {"title": row[0], "sold": row[1]} for row in top_products.all()
            ],
        }
    
    async def get_ai_suggestions(self, db: AsyncSession) -> dict:
        # Get customer data for analysis
        customers = await db.execute(
            select(User).where(User.purchase_count > 0).limit(100)
        )
        customer_list = [
            {
                "id": str(c.id),
                "name": c.name,
                "total_spent": float(c.total_spent),
                "purchase_count": c.purchase_count,
                "loyalty_level": c.loyalty_level,
                "last_purchase": str(c.last_purchase_at) if c.last_purchase_at else None,
            }
            for c in customers.scalars().all()
        ]
        
        # Get sales data
        sales_data = await self.get_dashboard_metrics(db)
        
        # Get AI suggestions
        fidel_customers = await customer_analyzer.identify_fidel_customers(customer_list)
        promo_suggestions = await promotion_generator.suggest_promotion(
            sales_data["sales"],
            sales_data["customers"]["loyalty_distribution"],
        )
        
        return {
            "fidel_customers": fidel_customers,
            "promotion_suggestions": promo_suggestions.get("suggestions", []),
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }
    
    async def approve_suggestion(self, db: AsyncSession, suggestion_type: str, suggestion_data: dict) -> dict:
        if suggestion_type == "promotion":
            promotion = Promotion(
                title=suggestion_data["title"],
                description=suggestion_data.get("description"),
                discount_type=suggestion_data["discount_type"],
                discount_value=suggestion_data["discount_value"],
                is_approved=True,
                ai_suggestion=suggestion_data,
            )
            db.add(promotion)
            await db.flush()
            return {"status": "approved", "id": str(promotion.id)}
        
        return {"status": "unknown_type"}


dashboard_service = DashboardService()
