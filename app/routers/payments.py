from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.stripe_service import stripe_service
from app.services.paypal_service import paypal_service
from app.services.order_service import order_service
from app.services.loyalty_service import loyalty_service
from app.services.promotion_service import promotion_service
from app.services.email_service import email_service
from app.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])


# ==================== STRIPE ====================

@router.post("/stripe/create")
async def create_stripe_session(order_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    success_url = f"{settings.frontend_url}/checkout/success?order_id={order_id}&payment=stripe"
    cancel_url = f"{settings.frontend_url}/checkout/cancel"
    
    result = await stripe_service.create_checkout_session(order, success_url, cancel_url)
    return result


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe_service.verify_webhook(payload, sig_header)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        order_id = session["metadata"]["order_id"]
        
        # Update order status
        order = await order_service.update_order_status(db, order_id, "paid")
        
        if order:
            # Update loyalty points
            await loyalty_service.update_user_loyalty(
                db, order.user_id, order.total_amount, order.id
            )
            
            # Check congratulation rules
            user = await db.get(User, order.user_id)
            if user:
                await promotion_service.check_congratulation_rules(db, user, order.id)
    
    return {"status": "success"}


# ==================== PAYPAL ====================

@router.post("/paypal/create")
async def create_paypal_order(order_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    result = await paypal_service.create_order(
        amount=str(order.total_amount),
        description=f"Orden #{str(order.id)[:8]}",
    )
    return result


@router.post("/paypal/capture")
async def capture_paypal_order(order_id: str, paypal_order_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await paypal_service.capture_order(paypal_order_id)
        
        # Update order status
        order = await order_service.update_order_status(db, order_id, "paid")
        
        if order:
            # Update loyalty points
            await loyalty_service.update_user_loyalty(
                db, order.user_id, order.total_amount, order.id
            )
            
            # Check congratulation rules
            user = await db.get(User, order.user_id)
            if user:
                await promotion_service.check_congratulation_rules(db, user, order.id)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/paypal/webhook")
async def paypal_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    # PayPal webhook verification would go here
    # For now, we rely on the capture endpoint
    return {"status": "ok"}
