from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.stripe_service import stripe_service
from app.services.order_service import order_service
from app.config import settings

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/stripe/create")
async def create_stripe_session(order_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    success_url = f"{settings.frontend_url}/checkout/success?order_id={order_id}"
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
        await order_service.update_order_status(db, order_id, "paid")
    
    return {"status": "success"}
