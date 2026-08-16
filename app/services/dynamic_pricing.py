"""Dynamic pricing intelligence (#3 on the innovation roadmap).

Computes recommended prices from demand signals, inventory pressure, and
optional time/holiday multipliers. Supports both read-only recommendations
and controlled auto-apply for products with dynamic_pricing_enabled.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.models.product_analytics import ProductAnalytics
from app.models.user_event import UserEvent

# Days of zero demand after which a high-stock product is flagged for clearance.
CLEARANCE_DAYS = 14
# Demand in the last 24h that, relative to the trailing week, marks a hot item.
HOT_MULTIPLIER = 1.5
LOW_STOCK = 5
HIGH_STOCK = 50


class DynamicPricingService:
    async def _aggregates(self, db: AsyncSession) -> dict[str, dict]:
        """Return per-product demand aggregates from user_events."""
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

        agg: dict[str, dict] = {}
        for e in events:
            pid = e.product_id
            if not pid:
                continue
            bucket = agg.setdefault(pid, {"views_24h": 0, "carts_24h": 0, "views_7d": 0})
            if e.created_at >= since_24h:
                if e.event_type == "view":
                    bucket["views_24h"] += 1
                else:
                    bucket["carts_24h"] += 1
            if e.event_type == "view":
                bucket["views_7d"] += 1
        return agg

    def _compute_multiplier(
        self,
        stock: int,
        views_24h: int,
        carts_24h: int,
        views_7d: int,
    ) -> tuple[float, str]:
        avg_daily = max(views_7d / 7.0, 0.05)
        demand_score = (views_24h + carts_24h) / avg_daily

        signal = "hold"
        multiplier = 1.0
        if carts_24h >= LOW_STOCK and demand_score >= HOT_MULTIPLIER:
            signal = "opportunity"
            multiplier = 1.05
        if views_24h == 0 and carts_24h == 0 and stock >= HIGH_STOCK:
            signal = "clearance"
            multiplier = 0.85
        return multiplier, signal

    async def get_recommendations(
        self,
        db: AsyncSession,
        limit: int = 20,
        product_ids: Optional[list[str]] = None,
    ) -> list[dict]:
        """Return pricing recommendations for active products."""
        stmt = select(Product).where(Product.is_active == True)
        if product_ids:
            stmt = stmt.where(Product.id.in_(product_ids))
        stmt = stmt.order_by(Product.title).limit(limit)
        products = (await db.execute(stmt)).scalars().all()

        agg = await self._aggregates(db)
        recommendations = []
        for p in products:
            pid = str(p.id)
            stock = int(p.stock) if p.stock is not None else -1
            current = float(p.price or 0)
            base = float(p.base_price) if p.base_price is not None else current

            bucket = agg.get(pid, {"views_24h": 0, "carts_24h": 0, "views_7d": 0})
            v24 = bucket["views_24h"]
            c24 = bucket["carts_24h"]
            v7 = bucket["views_7d"]

            multiplier, signal = self._compute_multiplier(stock, v24, c24, v7)
            suggested = round(base * multiplier, 2)

            recommendations.append(
                {
                    "product_id": pid,
                    "title": p.title,
                    "current_price": current,
                    "base_price": base,
                    "suggested_price": suggested,
                    "signal": signal,
                    "demand_24h_views": v24,
                    "demand_24h_cart_adds": c24,
                    "demand_7d_views": v7,
                    "stock": stock,
                    "dynamic_pricing_enabled": bool(p.dynamic_pricing_enabled),
                }
            )
        return recommendations

    async def simulate_price(
        self,
        db: AsyncSession,
        product_id: str,
        multiplier: float,
    ) -> dict:
        """Return the price for a product after applying a manual multiplier."""
        product = await db.get(Product, product_id)
        if not product:
            raise ValueError("Product not found")
        base = float(product.base_price) if product.base_price is not None else float(product.price or 0)
        return {
            "product_id": product_id,
            "base_price": base,
            "multiplier": multiplier,
            "simulated_price": round(base * multiplier, 2),
        }

    async def apply_recommendation(
        self,
        db: AsyncSession,
        product_id: str,
        new_price: float,
    ) -> Product:
        """Persist a new dynamic price for a product."""
        product = await db.get(Product, product_id)
        if not product:
            raise ValueError("Product not found")
        if product.base_price is None:
            product.base_price = product.price
        product.dynamic_price = Decimal(str(new_price))
        product.price = Decimal(str(new_price))
        product.price_updated_at = datetime.utcnow()
        await db.flush()
        return product

    async def toggle_auto_apply(
        self,
        db: AsyncSession,
        product_id: str,
        enabled: bool,
    ) -> Product:
        """Enable/disable automatic price updates for a product."""
        product = await db.get(Product, product_id)
        if not product:
            raise ValueError("Product not found")
        product.dynamic_pricing_enabled = enabled
        if enabled and product.base_price is None:
            product.base_price = product.price
        await db.flush()
        return product

    async def refresh_product_analytics(self, db: AsyncSession) -> int:
        """Recompute and store per-product analytics aggregates."""
        now = datetime.utcnow()
        since_24h = now - timedelta(hours=24)
        since_30d = now - timedelta(days=30)
        since_7d = now - timedelta(days=7)

        events = (
            await db.execute(
                select(UserEvent).where(UserEvent.created_at >= since_30d)
            )
        ).scalars().all()

        agg: dict[str, dict] = {}
        for e in events:
            pid = e.product_id
            if not pid:
                continue
            bucket = agg.setdefault(
                pid,
                {"views_24h": 0, "cart_adds_24h": 0, "sales_24h": 0, "sales_30d": 0, "views_7d": 0},
            )
            if e.event_type == "view":
                if e.created_at >= since_24h:
                    bucket["views_24h"] += 1
                if e.created_at >= since_7d:
                    bucket["views_7d"] += 1
            elif e.event_type == "cart_add":
                if e.created_at >= since_24h:
                    bucket["cart_adds_24h"] += 1
            elif e.event_type == "purchase":
                bucket["sales_30d"] += 1
                if e.created_at >= since_24h:
                    bucket["sales_24h"] += 1

        # Upsert aggregates
        count = 0
        for pid, values in agg.items():
            existing = (
                await db.execute(
                    select(ProductAnalytics).where(ProductAnalytics.product_id == pid)
                )
            ).scalar_one_or_none()
            if not existing:
                existing = ProductAnalytics(product_id=pid)
                db.add(existing)
            existing.views_24h = values["views_24h"]
            existing.cart_adds_24h = values["cart_adds_24h"]
            existing.sales_24h = values["sales_24h"]
            existing.sales_30d = values["sales_30d"]
            existing.avg_views_30d = values["views_7d"] // 7
            existing.recorded_at = now
            count += 1
        await db.flush()
        return count

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
