import stripe
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.config import settings
from app.database import get_db_session
from app.models.order import Order, OrderItem
from app.models.product import Product

stripe.api_key = settings.stripe_secret_key


class StripeService:
    async def create_checkout_session(self, order: Order, success_url: str, cancel_url: str) -> dict:
        # Eager-load order items and product details for line items.
        async with get_db_session() as db:
            result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id).options(selectinload(OrderItem.product))
            )
            items = result.scalars().all()

        line_items = []
        for item in items:
            product_name = item.product.title if item.product else f"Producto {item.product_id[:8]}"
            line_items.append({
                "price_data": {
                    "currency": "mxn",
                    "product_data": {"name": product_name},
                    "unit_amount": int(item.price_at_purchase * 100),
                },
                "quantity": item.quantity,
            })

        # Add shipping cost as a line item if applicable
        if order.shipping_amount and Decimal(str(order.shipping_amount)) > 0:
            line_items.append({
                "price_data": {
                    "currency": "mxn",
                    "product_data": {"name": "Envío"},
                    "unit_amount": int(Decimal(str(order.shipping_amount)) * 100),
                },
                "quantity": 1,
            })

        if not line_items:
            # Fallback to a single order-level line item if no items are found.
            line_items = [{
                "price_data": {
                    "currency": "mxn",
                    "product_data": {"name": f"Orden #{str(order.id)[:8]}"},
                    "unit_amount": int(order.total_amount * 100),
                },
                "quantity": 1,
            }]

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"order_id": str(order.id)},
        )
        return {"session_id": session.id, "url": session.url}
    
    def verify_webhook(self, payload: bytes, sig_header: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.stripe_webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")

    def retrieve_checkout_session(self, session_id: str):
        """Server-side confirmation of a Checkout Session.

        Used as a resilience fallback on /checkout/success: if the async
        webhook is delayed or missed, we confirm with Stripe directly and
        fulfill the order. Raises stripe.error.InvalidRequestError when the
        session does not exist / the API key is missing.
        """
        if not settings.stripe_secret_key or not session_id:
            raise ValueError("Stripe not configured or missing session_id")
        return stripe.checkout.Session.retrieve(session_id)


stripe_service = StripeService()
