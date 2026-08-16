"""Autonomous marketing campaigns engine.

Creates and executes lifecycle campaigns (post-purchase, cross-sell, review,
abandoned-cart recovery) and seasonal campaigns for Mexican holidays. Each
execution creates a `Campaign` record for tracking and enqueues emails through
`EmailQueue` for eventual delivery.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.campaign import Campaign
from app.models.email_queue import EmailQueue
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.abandoned_cart_service import abandoned_cart_service
from app.services.email_queue_service import email_queue_service
from app.ai.llm_router import llm_router, TaskType


# Mexican holiday calendar used by the daily seasonal trigger.
# Dates are refreshed yearly by configuration; for simplicity we keep a
# near-term rolling window and allow manual override via `seasonal_campaign`.
MEXICAN_HOLIDAYS = {
    "hot_sale": "2026-05-25",
    "san_valentin": "2026-02-14",
    "dia_nino": "2026-04-30",
    "dia_madre": "2026-05-10",
    "buen_fin": "2026-11-16",
    "dia_muertos": "2026-11-02",
    "navidad": "2026-12-25",
    "reyes_magos": "2027-01-06",
}


class CampaignEngine:
    async def on_order_placed(self, db: AsyncSession, order: Order) -> None:
        """Schedule lifecycle follow-ups after a paid order.

        Creates three scheduled campaigns:
        - thank-you email 1 hour later
        - cross-sell email 3 days later
        - review request 14 days later
        """
        user = await db.get(User, order.user_id)
        if not user or not user.email:
            return

        base_content = {"order_id": order.id, "user_id": user.id}
        await self._create_scheduled(
            db,
            campaign_type="post_purchase",
            name="Gracias por tu compra",
            target={**base_content},
            content={
                "subject": "Gracias por tu compra en Tienda Eaciot",
                "body": f"Hola {user.name or 'cliente'}, gracias por confiar en nosotros.",
            },
            hours=1,
        )
        await self._create_scheduled(
            db,
            campaign_type="cross_sell",
            name="Complementa tu compra",
            target={**base_content},
            content={
                "subject": "Descubre productos que complementan tu pedido",
                "body": "Basado en tu última compra, pensamos que estos productos te podrían interesar.",
            },
            days=3,
        )
        await self._create_scheduled(
            db,
            campaign_type="review_request",
            name="¿Qué opinas de tu compra?",
            target={**base_content},
            content={
                "subject": "Cuéntanos qué te pareció tu pedido",
                "body": "Tu opinión nos ayuda a mejorar y ayuda a otros compradores.",
            },
            days=14,
        )

    async def detect_abandoned_carts(self, db: AsyncSession) -> dict:
        """Find abandoned carts and enqueue recovery emails as campaigns."""
        candidates = await abandoned_cart_service.get_candidates(
            db, window_days=7, limit=500
        )
        campaigns_created = 0
        for c in candidates:
            # Idempotency: skip if we already have an active/completed recovery
            # campaign for this user in the last 7 days.
            recent = (
                await db.execute(
                    select(Campaign)
                    .where(Campaign.type == "abandoned_cart")
                    .where(Campaign.target_audience["user_id"].as_string() == c["user_id"])
                    .where(Campaign.created_at >= datetime.utcnow() - timedelta(days=7))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if recent:
                continue

            campaign = Campaign(
                name="Recuperación de carrito",
                type="abandoned_cart",
                status="active",
                target_audience={"user_id": c["user_id"], "email": c["email"]},
                content={
                    "products": c["products"],
                    "total_value": c["total_value"],
                    "name": c["name"],
                },
            )
            db.add(campaign)
            await db.flush()

            subject, body = await self._render_abandoned_cart_email(c)
            await email_queue_service.enqueue(
                db,
                to_email=c["email"],
                subject=subject,
                html_content=body,
                dedupe_key="CARRITO-ABANDONADO",
            )
            campaign.status = "completed"
            campaign.executed_at = datetime.utcnow()
            campaign.metrics = {"enqueued": 1}
            campaigns_created += 1

        await db.flush()
        return {"campaigns_created": campaigns_created}

    async def seasonal_campaign(
        self, db: AsyncSession, event: str
    ) -> Campaign | None:
        """Create a seasonal campaign for a Mexican holiday.

        Uses the LLM router for copy when available; falls back to templates.
        Returns None if a seasonal campaign for the event already exists.
        """
        existing = (
            await db.execute(
                select(Campaign)
                .where(Campaign.type == "seasonal")
                .where(Campaign.content["event"].as_string() == event)
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing:
            return None

        copy = await self._generate_seasonal_copy(event)
        campaign = Campaign(
            name=copy["name"],
            type="seasonal",
            status="scheduled",
            target_audience={"segment": "all_active"},
            content={
                "event": event,
                "subject": copy["subject"],
                "body": copy["body"],
            },
        )
        db.add(campaign)
        await db.flush()
        return campaign

    def get_upcoming_holidays(self, days: int = 7) -> dict[str, str]:
        """Return Mexican holidays within the next N days as {event: date_str}."""
        from datetime import date

        today = date.today()
        end = today + timedelta(days=days)
        upcoming: dict[str, str] = {}
        for event, event_date_str in MEXICAN_HOLIDAYS.items():
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
            days_until = (event_date - today).days
            if 0 <= days_until <= days:
                upcoming[event] = event_date_str
        return upcoming

    async def create_seasonal_campaigns_for_today(self, db: AsyncSession) -> dict:
        """Daily check: create seasonal campaigns for holidays within 7 days."""
        upcoming = self.get_upcoming_holidays(days=7)
        created: list[str] = []
        for event in upcoming:
            campaign = await self.seasonal_campaign(db, event)
            if campaign:
                created.append(event)
        await db.commit()
        return {"created": created}

    async def run_campaign(self, db: AsyncSession, campaign_id: str) -> dict:
        """Execute a campaign by enqueuing its emails."""
        campaign = await db.get(Campaign, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        if campaign.status == "completed":
            return {"enqueued": 0}

        enqueued = 0
        if campaign.type == "seasonal":
            enqueued = await self._execute_seasonal(db, campaign)
        elif campaign.type == "abandoned_cart":
            enqueued = await self._execute_abandoned_cart(db, campaign)
        elif campaign.type in ("post_purchase", "cross_sell", "review_request", "win_back", "new_arrival"):
            enqueued = await self._execute_single_user(db, campaign)
        else:
            enqueued = await self._execute_single_user(db, campaign)

        campaign.status = "completed"
        campaign.executed_at = datetime.utcnow()
        campaign.metrics = {"enqueued": enqueued}
        await db.flush()
        return {"enqueued": enqueued}

    # ── Helpers ─────────────────────────────────────────────────────────────

    async def _create_scheduled(
        self,
        db: AsyncSession,
        campaign_type: str,
        name: str,
        target: dict,
        content: dict,
        hours: int = 0,
        days: int = 0,
    ) -> Campaign:
        scheduled_at = datetime.utcnow() + timedelta(hours=hours, days=days)
        campaign = Campaign(
            name=name,
            type=campaign_type,
            status="scheduled",
            target_audience=target,
            content=content,
            scheduled_at=scheduled_at,
        )
        db.add(campaign)
        await db.flush()
        return campaign

    async def _execute_single_user(
        self, db: AsyncSession, campaign: Campaign
    ) -> int:
        user_id = campaign.target_audience.get("user_id")
        if not user_id:
            return 0
        user = await db.get(User, user_id)
        if not user or not user.email:
            return 0

        subject = campaign.content.get("subject", campaign.name)
        body = campaign.content.get("body", "")
        html = self._render_email_base(subject, body, user.name or "cliente")
        await email_queue_service.enqueue(db, user.email, subject, html)
        return 1

    async def _execute_abandoned_cart(
        self, db: AsyncSession, campaign: Campaign
    ) -> int:
        email = campaign.target_audience.get("email")
        if not email:
            return 0
        content = campaign.content or {}
        c = {
            "email": email,
            "name": content.get("name", ""),
            "products": content.get("products", []),
            "total_value": float(content.get("total_value", 0)),
        }
        subject, body = await self._render_abandoned_cart_email(c)
        await email_queue_service.enqueue(db, email, subject, body)
        return 1

    async def _execute_seasonal(self, db: AsyncSession, campaign: Campaign) -> int:
        subject = campaign.content.get("subject", campaign.name)
        body = campaign.content.get("body", "")
        users = (
            await db.execute(select(User).where(User.is_active == True).where(User.email.isnot(None)))
        ).scalars().all()

        enqueued = 0
        for user in users:
            html = self._render_email_base(subject, body, user.name or "cliente")
            await email_queue_service.enqueue(db, user.email, subject, html)
            enqueued += 1
        return enqueued

    async def _render_abandoned_cart_email(self, c: dict) -> tuple[str, str]:
        subject = "🧺 " + (c.get("name") or "cliente") + ", tu carrito te espera"
        titles = ", ".join(c.get("products", [])[:3]) or "tus productos"
        cart_url = f"{settings.frontend_url}/cart"
        body = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:20px;">
<h2 style="color:#f59e0b;">¿Te quedaste a medias?</h2>
<p>Hola {c.get("name") or "cliente"},</p>
<p>Dejaste estos productos en tu carrito: <strong>{titles}</strong>.</p>
<p style="text-align:center;">
  <a href="{cart_url}" style="display:inline-block;background:#f59e0b;color:#fff;padding:12px 24px;text-decoration:none;border-radius:6px;">Volver a mi carrito</a>
</p>
<p>Si tienes dudas, responde este correo y te ayudamos.</p>
</div>
</body></html>"""
        return subject, body

    def _render_email_base(self, subject: str, body: str, name: str) -> str:
        return f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;">
<div style="max-width:600px;margin:0 auto;padding:20px;">
<h2>{subject}</h2>
<p>Hola {name},</p>
<p>{body}</p>
<p style="margin-top:24px;color:#6b7280;font-size:14px;">&copy; 2026 Tienda Eaciot</p>
</div>
</body></html>"""

    async def _generate_seasonal_copy(self, event: str) -> dict:
        names = {
            "hot_sale": "Hot Sale México",
            "san_valentin": "San Valentín",
            "dia_nino": "Día del Niño",
            "dia_madre": "Día de las Madres",
            "buen_fin": "El Buen Fin",
            "dia_muertos": "Día de Muertos",
            "navidad": "Navidad",
            "reyes_magos": "Día de Reyes",
        }
        fallback = {
            "name": names.get(event, event),
            "subject": f"Ofertas especiales de {names.get(event, event)} en Tienda Eaciot",
            "body": f"Aprovecha nuestras promociones por {names.get(event, event)}. Envíos a Cuernavaca y todo Morelos.",
        }

        prompt = (
            f"Escribe un email promocional para la tienda Tienda Eaciot "
            f"con motivo de {names.get(event, event)}. "
            'Responde SOLO en JSON: {"name": "...", "subject": "...", "body": "..."}. '
            "El body es un párrafo corto y cálido en español."
        )
        try:
            data = await llm_router.generate_structured(
                prompt,
                system="Eres un copywriter de e-commerce en México.",
                task_type=TaskType.COPYWRITING,
            )
        except Exception:
            data = {}

        return {
            "name": data.get("name") or fallback["name"],
            "subject": data.get("subject") or fallback["subject"],
            "body": data.get("body") or fallback["body"],
        }


campaign_engine = CampaignEngine()
