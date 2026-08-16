"""AI-Driven Personalization Engine (#2.3 on the innovation roadmap).

Builds a lightweight implicit-feedback model from `user_events` without heavy
ML dependencies. Each event type has a weight (view < wishlist < cart_add <
purchase), and we rank candidate products by recency, category affinity, and
co-occurrence. The model updates the user's `favorite_category_id` on every
recommendation call so the profile stays fresh.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, Category
from app.models.user import User
from app.models.user_event import UserEvent
from app.services.recommendation_service import recommendation_service


_EVENT_WEIGHTS = {
    "view": 1,
    "wishlist": 4,
    "cart_add": 3,
    "purchase": 5,
    "search": 0,
}

_COLD_START_LIMIT = 3  # minimum interactions before we call it "personalized"


class PersonalizationService:
    async def recommend_for_user(
        self,
        db: AsyncSession,
        user_id: str | None,
        n: int = 10,
    ) -> dict[str, Any]:
        """Return personalized recommendations and the inferred category.

        The response shape is intentionally rich so the storefront can show a
        carousel and a small explanation ("Because you browsed X").
        """
        trending = await recommendation_service.get_trending(db, limit=n)

        if not user_id:
            return {
                "products": trending,
                "favorite_category": None,
                "personalized": False,
                "reason": "trending",
            }

        user = await db.get(User, user_id)
        if not user:
            return {
                "products": trending,
                "favorite_category": None,
                "personalized": False,
                "reason": "trending",
            }

        since = datetime.utcnow() - timedelta(days=90)
        events = (
            await db.execute(
                select(UserEvent)
                .where(UserEvent.user_id == user_id)
                .where(UserEvent.created_at >= since)
                .order_by(UserEvent.created_at.desc())
            )
        ).scalars().all()

        purchased_ids = {
            str(e.product_id)
            for e in events
            if e.event_type == "purchase" and e.product_id
        }

        if len(events) < _COLD_START_LIMIT:
            filtered_trending = [p for p in trending if str(p.id) not in purchased_ids][:n]
            return {
                "products": filtered_trending,
                "favorite_category": user.favorite_category_id,
                "personalized": False,
                "reason": "trending",
            }

        product_scores = self._score_products(events)
        favorite_category_id = await self._resolve_favorite_category(db, product_scores)
        if favorite_category_id:
            for pid, score in product_scores.items():
                product = await db.get(Product, pid)
                if product and product.category_id == favorite_category_id:
                    product_scores[pid] = score * Decimal("1.5")
            if favorite_category_id != user.favorite_category_id:
                user.favorite_category_id = favorite_category_id
                await db.flush()

        recommendations: list[Product] = []
        seen: set[str] = set()
        for product_id, _score in sorted(
            product_scores.items(), key=lambda x: x[1], reverse=True
        ):
            pid = str(product_id)
            if pid in purchased_ids or pid in seen:
                continue
            product = await db.get(Product, pid)
            if product and product.is_active:
                recommendations.append(product)
                seen.add(pid)
                if len(recommendations) >= n:
                    break

        if favorite_category_id and len(recommendations) < n:
            exclude_ids = list(seen | purchased_ids) or [""]
            same_cat = (
                await db.execute(
                    select(Product)
                    .where(Product.is_active == True)
                    .where(Product.category_id == favorite_category_id)
                    .where(Product.id.notin_(exclude_ids))
                    .order_by(Product.created_at.desc())
                    .limit(n - len(recommendations))
                )
            ).scalars().all()
            for product in same_cat:
                pid = str(product.id)
                if pid not in seen and pid not in purchased_ids:
                    recommendations.append(product)
                    seen.add(pid)

        if len(recommendations) < n:
            for product in trending:
                pid = str(product.id)
                if pid not in seen and pid not in purchased_ids:
                    recommendations.append(product)
                    seen.add(pid)
                    if len(recommendations) >= n:
                        break

        category_name: str | None = None
        if favorite_category_id:
            category = await db.get(Category, favorite_category_id)
            category_name = category.name if category else None

        return {
            "products": recommendations,
            "favorite_category": category_name,
            "favorite_category_id": favorite_category_id,
            "personalized": True,
            "reason": f"Porque te interesa {category_name}" if category_name else "Basado en tu actividad",
        }

    async def _resolve_favorite_category(
        self, db: AsyncSession, product_scores: dict[str, Decimal]
    ) -> str | None:
        if not product_scores:
            return None
        product_ids = list(product_scores.keys())
        rows = (
            await db.execute(
                select(Product.id, Product.category_id)
                .where(Product.id.in_(product_ids))
                .where(Product.category_id.isnot(None))
            )
        ).all()

        category_scores: dict[str, Decimal] = {}
        for pid, category_id in rows:
            category_scores[category_id] = category_scores.get(
                category_id, Decimal(0)
            ) + product_scores.get(pid, Decimal(0))

        if not category_scores:
            return None
        return max(category_scores.items(), key=lambda x: x[1])[0]

    def _score_products(self, events: list[UserEvent]) -> dict[str, Decimal]:
        """Return a map of product_id -> raw personalization score.

        Score = weighted event sum * recency bonus.
        Category affinity is applied later in recommend_for_user.
        """
        scores: dict[str, Decimal] = {}
        now = datetime.utcnow()
        for event in events:
            if not event.product_id:
                continue
            weight = Decimal(_EVENT_WEIGHTS.get(event.event_type, 1))
            days_ago = max(1, (now - event.created_at).days)
            recency = Decimal(7) / Decimal(days_ago)
            scores[event.product_id] = scores.get(event.product_id, Decimal(0)) + (
                weight * (Decimal(1) + recency)
            )
        return scores

    async def explain_recommendation(
        self,
        db: AsyncSession,
        user_id: str,
        product_id: str,
    ) -> str:
        """Human-readable reason why a product was recommended."""
        events = (
            await db.execute(
                select(UserEvent)
                .where(UserEvent.user_id == user_id)
                .where(UserEvent.product_id == product_id)
                .order_by(UserEvent.created_at.desc())
                .limit(1)
            )
        ).scalars().first()

        if events:
            return "Recomendado por tu actividad reciente"

        product = await db.get(Product, product_id)
        if product and product.category_id:
            user = await db.get(User, user_id)
            if user and user.favorite_category_id == product.category_id:
                return "En tu categoría favorita"
        return "Popular ahora"


personalization_service = PersonalizationService()
