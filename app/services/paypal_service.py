import httpx
import json as json_lib
from app.config import settings
from typing import Optional


class PayPalService:
    def __init__(self):
        self.client_id = settings.paypal_client_id
        self.client_secret = settings.paypal_client_secret
        self.mode = settings.paypal_mode
        self.webhook_id = settings.paypal_webhook_id
        self.base_url = (
            "https://api-m.sandbox.paypal.com"
            if self.mode == "sandbox"
            else "https://api-m.paypal.com"
        )

    async def get_access_token(self) -> str:
        """Get PayPal OAuth2 access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()
            return response.json()["access_token"]

    async def create_order(
        self,
        amount: str,
        currency: str = "MXN",
        description: str = "",
        return_url: str = "",
        cancel_url: str = "",
        custom_id: str = "",
    ) -> dict:
        """Create a PayPal order and return the full response (id, links, status)."""
        access_token = await self.get_access_token()

        purchase_unit: dict = {
            "amount": {
                "currency_code": currency,
                "value": amount,
            },
            "description": description,
        }
        if custom_id:
            purchase_unit["custom_id"] = custom_id

        body: dict = {
            "intent": "CAPTURE",
            "purchase_units": [purchase_unit],
        }

        if return_url or cancel_url:
            body["payment_source"] = {
                "paypal": {
                    "experience_context": {
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                    }
                }
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def capture_order(self, order_id: str) -> dict:
        """Capture a PayPal order that was created with intent=CAPTURE."""
        access_token = await self.get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_order_details(self, order_id: str) -> dict:
        """Get PayPal order details by ID."""
        access_token = await self.get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/checkout/orders/{order_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )
            response.raise_for_status()
            return response.json()

    async def refund_capture(
        self,
        capture_id: str,
        amount: Optional[str] = None,
        currency: str = "MXN",
    ) -> dict:
        """Refund a captured payment (full or partial)."""
        access_token = await self.get_access_token()

        refund_data: dict = {}
        if amount:
            refund_data = {
                "amount": {
                    "value": amount,
                    "currency_code": currency,
                }
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/payments/captures/{capture_id}/refund",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=refund_data,
            )
            response.raise_for_status()
            return response.json()

    async def verify_webhook_signature(
        self,
        payload: bytes,
        headers: dict,
    ) -> bool:
        """Verify a PayPal webhook notification.

        Calls PayPal's POST /v1/notifications/verify-webhook-signature when a
        webhook ID is configured.  In sandbox / dev without a webhook ID the
        call is skipped and the event is trusted.
        """
        if not self.webhook_id:
            # No webhook ID configured → accept (development mode).
            return True

        transmission_id = headers.get("paypal-transmission-id", "")
        transmission_time = headers.get("paypal-transmission-time", "")
        cert_url = headers.get("paypal-cert-url", "")
        auth_algo = headers.get("paypal-auth-algo", "")
        transmission_sig = headers.get("paypal-transmission-sig", "")

        try:
            access_token = await self.get_access_token()
            verify_body = {
                "auth_algo": auth_algo,
                "cert_url": cert_url,
                "transmission_id": transmission_id,
                "transmission_sig": transmission_sig,
                "transmission_time": transmission_time,
                "webhook_event": json_lib.loads(payload),
                "webhook_id": self.webhook_id,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/v1/notifications/verify-webhook-signature",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=verify_body,
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    return resp.json().get("verification_status") == "SUCCESS"
        except Exception:
            pass

        return False


paypal_service = PayPalService()
