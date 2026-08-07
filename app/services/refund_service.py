from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from app.models.refund import Refund
from app.models.order import Order
from app.schemas.refund import RefundCreate
from app.services.stripe_service import stripe_service
from app.services.paypal_service import paypal_service


class RefundService:
    async def create_refund_request(self, db: AsyncSession, user_id: UUID, data: RefundCreate) -> Refund:
        """Create a refund request"""
        # Verify order belongs to user
        order = await db.get(Order, data.order_id)
        if not order or str(order.user_id) != str(user_id):
            raise ValueError("Order not found")
        
        if order.status not in ["paid", "delivered"]:
            raise ValueError("Order cannot be refunded")
        
        # Check if refund amount is valid
        if data.amount > order.total_amount:
            raise ValueError("Refund amount exceeds order total")
        
        refund = Refund(
            order_id=data.order_id,
            user_id=user_id,
            amount=data.amount,
            reason=data.reason,
            refund_method=data.refund_method,
            status="pending",
        )
        db.add(refund)
        await db.flush()
        return refund
    
    async def approve_refund(self, db: AsyncSession, refund_id: UUID, admin_notes: str = "") -> Optional[Refund]:
        """Approve a refund request"""
        result = await db.execute(select(Refund).where(Refund.id == refund_id))
        refund = result.scalar_one_or_none()
        
        if not refund or refund.status != "pending":
            return None
        
        refund.status = "approved"
        refund.admin_notes = admin_notes
        await db.flush()
        return refund
    
    async def process_refund(self, db: AsyncSession, refund_id: UUID) -> Optional[Refund]:
        """Process an approved refund"""
        result = await db.execute(select(Refund).where(Refund.id == refund_id))
        refund = result.scalar_one_or_none()
        
        if not refund or refund.status != "approved":
            return None
        
        # Get order to determine payment method
        order = await db.get(Order, refund.order_id)
        
        try:
            if order.payment_method == "stripe" and order.payment_id:
                # Process Stripe refund
                stripe_refund = stripe_service.create_refund(
                    payment_intent_id=order.payment_id,
                    amount=int(refund.amount * 100),  # Convert to cents
                )
                refund.payment_refund_id = stripe_refund.id
                
            elif order.payment_method == "paypal" and order.payment_id:
                # Process PayPal refund
                paypal_refund = await paypal_service.refund_capture(
                    capture_id=order.payment_id,
                    amount=str(refund.amount),
                )
                refund.payment_refund_id = paypal_refund.get("id")
            
            refund.status = "completed"
            refund.processed_at = func.now()
            
            # Update order status
            order.status = "refunded"
            
        except Exception as e:
            refund.status = "failed"
            refund.admin_notes = f"Error: {str(e)}"
        
        await db.flush()
        return refund
    
    async def reject_refund(self, db: AsyncSession, refund_id: UUID, reason: str) -> Optional[Refund]:
        """Reject a refund request"""
        result = await db.execute(select(Refund).where(Refund.id == refund_id))
        refund = result.scalar_one_or_none()
        
        if not refund or refund.status != "pending":
            return None
        
        refund.status = "rejected"
        refund.admin_notes = reason
        await db.flush()
        return refund
    
    async def get_user_refunds(self, db: AsyncSession, user_id: UUID) -> List[Refund]:
        """Get all refunds for a user"""
        result = await db.execute(
            select(Refund)
            .where(Refund.user_id == user_id)
            .order_by(Refund.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_all_refunds(self, db: AsyncSession, status: Optional[str] = None) -> List[Refund]:
        """Get all refunds (admin)"""
        query = select(Refund)
        if status:
            query = query.where(Refund.status == status)
        query = query.order_by(Refund.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()


refund_service = RefundService()
