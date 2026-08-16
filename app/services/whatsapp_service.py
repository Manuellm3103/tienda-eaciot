"""WhatsApp Business commerce integration.

Handles incoming messages from Meta's WhatsApp Cloud API webhooks, looks up or
creates customers by phone number, routes messages to the existing AI shopping
assistant, and formats replies for WhatsApp.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.services.chat_service import chat_service


class WhatsAppCommerceService:
    async def handle_incoming_message(
        self, db: AsyncSession, phone: str, message: str
    ) -> dict:
        """Process an inbound WhatsApp message and return the AI reply."""
        user = await self._find_or_create_user(db, phone)
        response = await chat_service.chat(
            db,
            message=message,
            user_id=str(user.id),
        )
        answer = response.get("answer", "No entendí bien, ¿puedes reformular?")
        products = response.get("products", []) or []

        formatted = self._format_reply(answer, products)
        await self._send_whatsapp_reply(phone, formatted)

        if products:
            await self.send_product_cards(phone, products)

        return {
            "status": "ok",
            "reply": formatted,
            "products_count": len(products),
        }

    async def _find_or_create_user(
        self, db: AsyncSession, phone: str
    ) -> User:
        """Look up a user by phone; create a WhatsApp-only user if missing."""
        cleaned = self._clean_phone(phone)
        result = await db.execute(select(User).where(User.phone == cleaned))
        user = result.scalar_one_or_none()
        if user:
            return user

        user = User(
            email=f"whatsapp+{cleaned}@eaciot.whatsapp",
            name=f"WhatsApp {cleaned}",
            phone=cleaned,
            is_guest=False,
        )
        db.add(user)
        await db.flush()
        return user

    def _clean_phone(self, phone: str) -> str:
        """Normalize phone to digits only."""
        return "".join(c for c in (phone or "") if c.isdigit())

    def _format_reply(self, answer: str, products: list[dict]) -> str:
        """Format the AI reply and optional product cards for WhatsApp."""
        lines = [answer]
        if products:
            lines.append("")
            lines.append("*Productos sugeridos:*")
            for p in products[:5]:
                title = p.get("title", "Producto")
                price = p.get("price")
                price_str = f" - ${float(price):.2f}" if price is not None else ""
                lines.append(f"• {title}{price_str}")
        return "\n".join(lines)

    async def send_product_cards(
        self, phone: str, products: list[dict]
    ) -> None:
        """Stub for rich WhatsApp product cards.

        In production this would call Meta's Messages API with a product
        catalog message or a list of interactive reply buttons.
        """
        # No-op stub: the formatted reply already includes product titles.
        # Future implementation: POST to
        # https://graph.facebook.com/vX.X/<PHONE_NUMBER_ID>/messages
        pass

    async def _send_whatsapp_reply(self, phone: str, text: str) -> None:
        """Send a text reply back to the WhatsApp user.

        This is a no-op stub when WhatsApp credentials are not configured.
        """
        if not settings.whatsapp_phone_number_id or not settings.whatsapp_access_token:
            return

        # Future implementation: call Meta Graph API
        # url = (
        #     f"https://graph.facebook.com/v18.0/{settings.whatsapp_phone_number_id}/messages"
        # )
        # headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
        # payload = {
        #     "messaging_product": "whatsapp",
        #     "to": phone,
        #     "type": "text",
        #     "text": {"body": text},
        # }
        # async with httpx.AsyncClient() as client:
        #     await client.post(url, headers=headers, json=payload)


whatsapp_service = WhatsAppCommerceService()
