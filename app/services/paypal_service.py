import httpx
from app.config import settings
from typing import Optional


class PayPalService:
    def __init__(self):
        self.client_id = settings.paypal_client_id
        self.client_secret = settings.paypal_client_secret
        self.mode = settings.paypal_mode
        self.base_url = "https://api-m.sandbox.paypal.com" if self.mode == "sandbox" else "https://api-m.paypal.com"
    
    async def get_access_token(self) -> str:
        """Get PayPal access token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                auth=(self.client_id, self.client_secret),
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()
            return response.json()["access_token"]
    
    async def create_order(self, amount: str, currency: str = "MXN", description: str = "") -> dict:
        """Create PayPal order"""
        access_token = await self.get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "intent": "CAPTURE",
                    "purchase_units": [
                        {
                            "amount": {
                                "currency_code": currency,
                                "value": amount,
                            },
                            "description": description,
                        }
                    ],
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def capture_order(self, order_id: str) -> dict:
        """Capture PayPal order"""
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
        """Get PayPal order details"""
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
    
    async def refund_capture(self, capture_id: str, amount: Optional[str] = None, currency: str = "MXN") -> dict:
        """Refund a captured payment"""
        access_token = await self.get_access_token()
        
        refund_data = {}
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


paypal_service = PayPalService()
