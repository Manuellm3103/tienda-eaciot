"""Dynamic pricing intelligence (#3 on the innovation roadmap).

Read-only recommender: it computes a suggested price and an action signal per
product from recent behavioral demand (user_events) and inventory pressure.
It NEVER mutates prices — the store owner decides whether to apply a suggestion,
so customers only ever see a discount, not an unexplained "AI price".
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.models.user_event import UserEvent

# Days of zero demand after which a high-stock product is flagged for clearance.
CLEARANCE_DAYS = 14
# Demand in the last 24h that, relative to the trailing week, marks a hot item.
HOT_MULTIPLIER = 1.5
LOW_STOCK = 5
HIGH_STOCK = 50


class DynamicPricingService:
    async def get_recommendations(self, db: AsyncSession, limit: int = 20) -> list[dict]:
        products = (
            await db.execute(
                select(Product).where(Product.is_active == True).order_by(Product.title)
            )
        ).scalars().all()

        now = datetime.utcnow()
        since_24h = now - timedelta(hours=24)
        since_7d = now - timedelta(days=7)

        events = (
            await db.execute(
                select(UserEvent)
                .where(UserEvent.created_at >= since_7d)
                .where(UserEvent.event_type.in_(["view", "cart_add"]))
            )
        ).scalars().all()

        views_24h: dict[str, int] = {}
        views_7d: dict[str, int] = {}
        carts_24h: dict[str, int] = {}
        for e in events:
            pid = e.product_id
            if not pid:
                continue
            if e.created_at >= since_24h:
                if e.event_type == "view":
                    views_24h[pid] = views_24h.get(pid, 0) + 1
                else:
                    carts_24h[pid] = carts_24h.get(pid, 0) + 1
            if e.event_type == "view":
                views_7d[pid] = views_7d.get(pid, 0) + 1

        recommendations = []
        for p in products[:limit]:
            pid = str(p.id)
            stock = int(p.stock) if p.stock is not None else -1
            current = float(p.price or 0)

            v24 = views_24h.get(pid, 0)
            c24 = carts_24h.get(pid, 0)
            v7 = views_7d.get(pid, 0)

            # avg daily views over the trailing 7 days
            avg_daily = max(v7 / 7.0, 0.05)
            demand_score = (v24 + c24) / avg_daily

            signal = "hold"
            multiplier = 1.0
            if c24 >= LOW_STOCK and demand_score >= HOT_MULTIPLIER:
                signal = "opportunity"
                multiplier = 1.05  # strong demand — small upward room
            if v24 == 0 and c24 == 0 and stock >= HIGH_STOCK:
                signal = "clearance"
                multiplier = 0.85  # slow mover — recommend a discount

            suggested = round(current * multiplier, 2)
            recommendations.append(
                {
                    "product_id": pid,
                    "title": p.title,
                    "current_price": current,
                    "suggested_price": suggested,
                    "signal": signal,
                    "demand_24h_views": v24,
                    "demand_24h_cart_adds": c24,
                    "demand_7d_views": v7,
                    "stock": stock,
                }
            )
        return recommendations

    async def get_insights(self, db: AsyncSession) -> dict:
        """Dashboard summary of the pricing state."""
        recs = await self.get_recommendations(db, limit=500)
        by_signal = {"opportunity": 0, "hold": 0, "clearance": 0}
        for r in recs:
            by_signal[r["signal"]] = by_signal.get(r["signal"], 0) + 1
        return {
            "total_products": len(recs),
            "signals": by_signal,
            "clearance_candidates": by_signal["clearance"],
            "opportunity_items": by_signal["opportunity"],
        }


dynamic_pricing = DynamicPricingService()
