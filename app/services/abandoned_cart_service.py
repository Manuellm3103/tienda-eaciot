"""Abandoned cart recovery (#7 on the innovation roadmap).

Detects identified users who added products to their cart (cart_add events)
but never completed a paid order afterwards, then drafts a recovery email via
the dual-LLM router and enqueues it in EmailQueue. The cron worker
(scripts/process_emails.py) is responsible for the actual SMTP delivery, so
this service only enqueues — never double-sends.

Only identified users (user_id != null) can be recovered: anonymous carts have
no email address on file, so they are surfaced as a count but not emailed.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.product import Product
from app.models.order import Order
from app.models.user_event import UserEvent
from app.models.email_queue import EmailQueue
from app.ai.llm_router import llm_router, TaskType
from app.config import settings

# Prefix every recovery subject so we can idempotently dedupe candidates.
SUBJECT_PREFIX = "🧺 "
DEDUPE_MARKER = "CARRITO-ABANDONADO"


class AbandonedCartService:
    async def get_candidates(
        self, db: AsyncSession, window_days: int = 3, limit: int = 50
    ) -> list[dict]:
        """Users who added to cart recently but have no paid order afterwards."""
        now = datetime.utcnow()
        since = now - timedelta(days=window_days)

        events = (
            await db.execute(
                select(UserEvent)
                .where(UserEvent.event_type == "cart_add")
                .where(UserEvent.created_at >= since)
                .where(UserEvent.user_id.isnot(None))
                .order_by(UserEvent.created_at.desc())
            )
        ).scalars().all()

        per_user: dict[str, dict] = {}
        for e in events:
            info = per_user.setdefault(
                e.user_id, {"last_at": e.created_at, "product_ids": []}
            )
            if e.product_id and e.product_id not in info["product_ids"]:
                info["product_ids"].append(e.product_id)

        candidates = []
        for uid, info in per_user.items():
            user = await db.get(User, uid)
            if not user or not user.email:
                continue

            paid_after = (
                await db.execute(
                    select(Order.id)
                    .where(Order.user_id == uid)
                    .where(Order.status == "paid")
                    .where(Order.created_at >= info["last_at"])
                    .limit(1)
                )
            ).first()
            if paid_after:
                continue  # completed a purchase — not abandoned

            already_queued = (
                await db.execute(
                    select(EmailQueue.id)
                    .where(EmailQueue.to_email == user.email)
                    .where(EmailQueue.subject.like(f"{SUBJECT_PREFIX}%"))
                    .limit(1)
                )
            ).first()
            if already_queued:
                continue  # already recovered (or queued) for this user

            products, total = [], Decimal("0")
            for pid in info["product_ids"]:
                product = await db.get(Product, pid)
                if product:
                    products.append(product.title)
                    total += product.price or Decimal("0")

            hours = int((now - info["last_at"]).total_seconds() // 3600)
            candidates.append(
                {
                    "user_id": uid,
                    "email": user.email,
                    "name": user.name or "",
                    "last_activity_at": info["last_at"].isoformat(),
                    "hours_inactive": hours,
                    "products": products,
                    "total_value": float(total),
                }
            )

        candidates.sort(key=lambda c: c["hours_inactive"], reverse=True)
        return candidates[:limit]

    async def enqueue_recovery_emails(
        self, db: AsyncSession, user_ids: list[str] | None = None
    ) -> dict:
        """Draft + enqueue a recovery email per candidate. Never sends directly."""
        candidates = await self.get_candidates(db, window_days=7, limit=500)
        if user_ids:
            wanted = set(user_ids)
            candidates = [c for c in candidates if c["user_id"] in wanted]

        for c in candidates:
            subject, hook = await self._generate_copy(c)
            db.add(
                EmailQueue(
                    to_email=c["email"],
                    subject=subject,
                    html_content=self._render_email(c, hook),
                )
            )

        await db.commit()
        return {"enqueued": len(candidates), "skipped": 0}

    async def _generate_copy(self, c: dict) -> tuple[str, str]:
        """AI subject + opening hook via the copywriting route, with fallbacks."""
        titles = ", ".join(c["products"][:3]) or "tus productos"
        name = c["name"] or "cliente"
        prompt = (
            f"Escribe un email de carrito abandonado en español para {name}. "
            f"Productos en su carrito: {titles}. "
            f"Valor total: ${c['total_value']:.2f}. "
            'Responde SOLO en JSON: {"subject": "...", "hook": "..."}. '
            "El hook es una frase breve y cálida que abre el email."
        )
        data = await llm_router.generate_structured(
            prompt,
            system="Eres un copywriter de e-commerce que convierte sin ser agresivo.",
            task_type=TaskType.COPYWRITING,
        )
        subject = SUBJECT_PREFIX + (data.get("subject") or "Tu carrito te espera")
        hook = (data.get("hook") or "").strip()
        return subject[:220], hook[:500]

    def _render_email(self, c: dict, hook: str) -> str:
        name = c["name"] or "cliente"
        items = "".join(
            f"<li style='margin:6px 0;'>{p}</li>" for p in c["products"]
        ) or "<li>Tus productos favoritos</li>"
        hook_html = f"<p style='font-size:16px;color:#4b5563;'>{hook}</p>" if hook else ""
        cart_url = f"{settings.frontend_url}/cart"
        # Embedded marker allows future dedup/audit of recovery emails.
        return f"""<!DOCTYPE html>
<html>
<head><style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
    .header {{ background: #f59e0b; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
    .content {{ background: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; }}
    .button {{ display: inline-block; background: #f59e0b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 20px 0; }}
    .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 14px; }}
</style></head>
<body>
    <div class="container">
        <div class="header"><h1>¿Te quedaste a medias? 🛒</h1></div>
        <div class="content">
            <h2>Hola {name},</h2>
            {hook_html}
            <p>Notamos que dejaste estos productos en tu carrito:</p>
            <ul style="padding-left:18px;">{items}</ul>
            <p style="text-align:center;">
                <a href="{cart_url}" class="button">Volver a mi carrito</a>
            </p>
            <p>Si tienes cualquier duda, responde este correo y te ayudamos.</p>
        </div>
        <div class="footer">
            <p>&copy; 2026 Tienda Eaciot. Todos los derechos reservados.</p>
            <!-- {DEDUPE_MARKER} -->
        </div>
    </div>
</body>
</html>"""


abandoned_cart_service = AbandonedCartService()
