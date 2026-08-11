from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.order import OrderCreate


class OrderService:
    async def create_order(self, db: AsyncSession, user_id: UUID, data: OrderCreate) -> Order:
        # Get products and calculate totals
        items_data = []
        subtotal = Decimal("0")
        
        for item in data.items:
            product = await db.get(Product, item.product_id)
            if not product or not product.is_active:
                raise ValueError(f"Product {item.product_id} not found or inactive")
            
            item_total = product.price * item.quantity
            subtotal += item_total
            items_data.append({
                "product_id": product.id,
                "quantity": item.quantity,
                "price_at_purchase": product.price,
            })
        
        # Create order
        order = Order(
            user_id=user_id,
            subtotal=subtotal,
            total_amount=subtotal,  # Will be updated with discounts/shipping
            shipping_address=data.shipping_address,
        )
        db.add(order)
        await db.flush()
        
        # Create order items
        for item_data in items_data:
            order_item = OrderItem(order_id=order.id, **item_data)
            db.add(order_item)
        
        await db.flush()
        return order
    
    async def get_user_orders(self, db: AsyncSession, user_id: UUID) -> List[Order]:
        result = await db.execute(
            select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_order(self, db: AsyncSession, order_id: UUID) -> Optional[Order]:
        result = await db.execute(select(Order).where(Order.id == order_id))
        return result.scalar_one_or_none()
    
    async def update_order_status(self, db: AsyncSession, order_id: UUID, status: str) -> Optional[Order]:
        order = await self.get_order(db, order_id)
        if not order:
            return None
        order.status = status
        await db.flush()
        return order
    
    async def mark_order_paid(self, db: AsyncSession, order_id: UUID, payment_method: str, payment_id: str) -> Optional[Order]:
        order = await self.get_order(db, order_id)
        if not order:
            return None
        order.status = "paid"
        order.payment_method = payment_method
        order.payment_id = payment_id
        await db.flush()
        return order


order_service = OrderService()
