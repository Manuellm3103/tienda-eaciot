from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.models.shipping import Shipment
from app.services.stripe_service import stripe_service
from app.services.paypal_service import paypal_service
from app.services.order_service import order_service
from app.services.loyalty_service import loyalty_service
from app.services.promotion_service import promotion_service
from app.services.email_service import email_service
from app.services.shipping_service import shipping_service
from app.config import settings
from decimal import Decimal
import uuid

router = APIRouter(prefix="/payments", tags=["payments"])


# ── helpers ──────────────────────────────────────────────────────────────

def _extract_approval_url(paypal_response: dict) -> str:
    """Walk the 'links' array of a PayPal order response and return the
    'approve' (payer-action) URL, or an empty string."""
    for link in paypal_response.get("links", []):
        if link.get("rel") == "payer-action" or link.get("rel") == "approve":
            return link.get("href", "")
    return ""


def _first_capture_id(paypal_response: dict) -> str:
    """Dig a capture ID out of a completed PayPal order / capture response."""
    for unit in paypal_response.get("purchase_units", []):
        captures = unit.get("payments", {}).get("captures", [])
        if captures:
            return captures[0].get("id", "")
    return paypal_response.get("id", "")


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


# ── PAYPAL ───────────────────────────────────────────────────────────────

@router.post("/paypal/create")
async def create_paypal_order(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a PayPal order for an existing DB order.

    Returns ``{paypal_order_id, approval_url}`` so the frontend can redirect
    the buyer to PayPal for approval.
    """
    order = await order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return_url = f"{settings.frontend_url}/checkout/success?order_id={order_id}&payment=paypal"
    cancel_url = f"{settings.frontend_url}/checkout/cancel"

    result = await paypal_service.create_order(
        amount=str(order.total_amount),
        description=f"Orden #{str(order.id)[:8]}",
        return_url=return_url,
        cancel_url=cancel_url,
        custom_id=str(order.id),
    )

    paypal_order_id = result.get("id", "")
    approval_url = _extract_approval_url(result)

    return JSONResponse({
        "paypal_order_id": paypal_order_id,
        "approval_url": approval_url,
    })


@router.post("/paypal/capture")
async def capture_paypal_order(
    order_id: str,
    paypal_order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Capture a previously-created PayPal order and fulfill the DB order.

    Called by the frontend after the buyer returns from PayPal approval.
    Returns the capture result and sets a ``Set-Cookie`` header that clears
    the client-side cart.
    """
    try:
        result = await paypal_service.capture_order(paypal_order_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    capture_id = _first_capture_id(result)
    await _fulfill_order(db, order_id, "paypal", capture_id)
    await db.commit()

    # Clear the client-side cart cookie
    response = JSONResponse(result)
    response.set_cookie(
        key="cart",
        value="{}",
        max_age=0,
        httponly=False,
        samesite="lax",
    )
    return response


@router.post("/paypal/webhook")
async def paypal_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle incoming PayPal webhook notifications.

    Processed events: **PAYMENT.CAPTURE.COMPLETED**, **CHECKOUT.ORDER.APPROVED**.

    Idempotency is guaranteed by the payment ID stored on the order — the same
    payment is never processed twice.
    """
    payload = await request.body()
    headers = {
        "paypal-transmission-id": request.headers.get("paypal-transmission-id", ""),
        "paypal-transmission-time": request.headers.get("paypal-transmission-time", ""),
        "paypal-cert-url": request.headers.get("paypal-cert-url", ""),
        "paypal-auth-algo": request.headers.get("paypal-auth-algo", ""),
        "paypal-transmission-sig": request.headers.get("paypal-transmission-sig", ""),
    }

    # Verify signature
    valid = await paypal_service.verify_webhook_signature(payload, headers)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid PayPal signature")

    event_body = __import__("json").loads(payload)
    event_type = event_body.get("event_type", "")

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        resource = event_body.get("resource", {})
        # Extract our order_id from the purchase_unit's custom_id
        purchase_units = resource.get("purchase_units", []) or []
        custom_id = ""
        if purchase_units:
            # The capture resource may carry custom_id on its purchase_unit
            # reference.  Fall back to the supplementary_data / invoice data.
            custom_id = purchase_units[0].get("custom_id", "")
        if not custom_id:
            # Try the additional_data path available on some event versions
            custom_id = (
                resource.get("supplementary_data", {})
                .get("related_ids", {})
                .get("order_id", "")
            ) or resource.get("custom_id", "")

        capture_id = resource.get("id", "")

        if custom_id:
            await _fulfill_order(db, custom_id, "paypal", capture_id)
            await db.commit()

    elif event_type == "CHECKOUT.ORDER.APPROVED":
        # Order approved but not yet captured — no fulfillment yet.
        # We just acknowledge; the frontend will call /capture to finalize.
        pass

    return {"status": "ok"}
