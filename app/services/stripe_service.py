import stripe
from app.config import settings
from app.models.order import Order

stripe.api_key = settings.stripe_secret_key


class StripeService:
    async def create_checkout_session(self, order: Order, success_url: str, cancel_url: str) -> dict:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "mxn",
                        "product_data": {
                            "name": f"Orden #{str(order.id)[:8]}",
                        },
                        "unit_amount": int(order.total_amount * 100),
                    },
                    "quantity": 1,
                }
            ],
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


stripe_service = StripeService()
