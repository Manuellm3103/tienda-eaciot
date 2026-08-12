from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.services.stripe_service import stripe_service
from app.services.order_service import order_service
from app.services.loyalty_service import loyalty_service
from app.services.promotion_service import promotion_service
from app.services.email_service import email_service
from app.services.shipping_service import shipping_service
from app.config import settings
from decimal import Decimal

router = APIRouter(prefix="/payments", tags=["payments"])


# ── helpers ──────────────────────────────────────────────────────────────


async def _fulfill_order(
    db: AsyncSession,
    order_id: str,
    payment_method: str,
    payment_id: str,
):
    """Idempotent order fulfillment after a successful payment.

    * Marks the order as **paid**
    * Creates a pending **shipment**
    * Updates **loyalty** points
    * Checks **congratulation** rules
    * Sends a confirmation **email**
    """
    order = await order_service.get_order(db, order_id)
    if not order:
        return None

    # ── idempotency: skip if already paid ──
    if order.status == "paid":
        return order

    # 1. Mark order paid
    order = await order_service.mark_order_paid(
        db, order_id, payment_method, payment_id,
    )
    if not order:
        return None

    # 2. Create a pending shipment
    from app.schemas.shipping import ShipmentCreate
    try:
        shipment_data = ShipmentCreate(
            order_id=order.id,
            carrier="pending",
            tracking_number=None,
            weight=Decimal("0.5"),
            shipping_cost=Decimal("0.00"),
        )
        await shipping_service.create_shipment(db, shipment_data)
    except Exception:
        pass  # shipment is best-effort; never block fulfillment

    # 3. Update loyalty points
    await loyalty_service.update_user_loyalty(
        db, order.user_id, order.total_amount, order.id,
    )

    # 4. Check congratulation rules
    user = await db.get(User, order.user_id)
    if user:
        await promotion_service.check_congratulation_rules(db, user, order.id)

    # 5. Send confirmation email (best-effort)
    if user:
        await email_service.send_order_confirmation_email(
            to_email=user.email,
            name=user.name or user.email,
            order_id=str(order.id),
            total=float(order.total_amount),
        )

    return order


# ── STRIPE ───────────────────────────────────────────────────────────────

@router.post("/stripe/create")
async def create_stripe_session(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    success_url = f"{settings.frontend_url}/checkout/success?order_id={order_id}&payment=stripe"
    cancel_url = f"{settings.frontend_url}/checkout/cancel"

    result = await stripe_service.create_checkout_session(order, success_url, cancel_url)
    return result


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe_service.verify_webhook(payload, sig_header)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type")
    if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        session = event["data"]["object"]
        order_id = session.get("metadata", {}).get("order_id")
        if order_id:
            payment_intent = session.get("payment_intent") or session.get("id")
            await _fulfill_order(db, order_id, "stripe", payment_intent)
            await db.commit()

    return {"status": "success"}
