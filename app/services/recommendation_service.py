"""Product recommendation engine (#4 on the innovation roadmap).

Built on the behavioral `user_events` foundation: trending items are ranked by
recent views + cart-adds, and related items come from co-occurrence (products
interacted with by the same user or session). Every path falls back gracefully
to newest / same-category products so the storefront never renders empty.
"""
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.models.user_event import UserEvent


class RecommendationService:
    async def get_trending(self, db: AsyncSession, limit: int = 6) -> list[Product]:
        """Products with the most behavioral demand in the last 7 days."""
        since = datetime.utcnow() - timedelta(days=7)
        rows = (
            await db.execute(
                select(UserEvent.product_id, func.count(UserEvent.id))
                .where(UserEvent.product_id.isnot(None))
                .where(UserEvent.event_type.in_(["view", "cart_add"]))
                .where(UserEvent.created_at >= since)
                .group_by(UserEvent.product_id)
                .order_by(func.count(UserEvent.id).desc())
                .limit(limit)
            )
        ).all()

        products, seen = [], set()
        for pid, _count in rows:
            product = await db.get(Product, pid)
            if product and product.is_active and product.id not in seen:
                products.append(product)
                seen.add(product.id)

        if len(products) < limit:
            newest = (
                await db.execute(
                    select(Product)
                    .where(Product.is_active == True)
                    .order_by(Product.created_at.desc())
                    .limit(limit)
                )
            ).scalars().all()
            for product in newest:
                if product.id not in seen and len(products) < limit:
                    products.append(product)
                    seen.add(product.id)
        return products

    async def get_related(
        self, db: AsyncSession, product_id: str, limit: int = 4
    ) -> list[Product]:
        """Products co-viewed/co-carted with this one, falling back to category."""
        contexts = (
            await db.execute(
                select(UserEvent.user_id, UserEvent.session_id)
                .where(UserEvent.product_id == product_id)
                .where(UserEvent.event_type.in_(["view", "cart_add"]))
                .distinct()
            )
        ).all()

        co_ids: list[str] = []
        for user_id, session_id in contexts:
            query = select(UserEvent.product_id).where(
                UserEvent.product_id != product_id
            )
            if user_id:
                query = query.where(UserEvent.user_id == user_id)
            elif session_id:
                query = query.where(UserEvent.session_id == session_id)
            else:
                continue
            result = (await db.execute(query.limit(limit))).scalars().all()
            co_ids.extend(result)

        products, seen = [], set()
        for pid in co_ids:
            if pid in seen:
                continue
            seen.add(pid)
            product = await db.get(Product, pid)
            if product and product.is_active:
                products.append(product)
                if len(products) >= limit:
                    break

        if len(products) < limit:
            source = await db.get(Product, product_id)
            if source and source.category_id:
                same_cat = (
                    await db.execute(
                        select(Product)
                        .where(Product.is_active == True)
                        .where(Product.category_id == source.category_id)
                        .where(Product.id != product_id)
                        .limit(limit)
                    )
                ).scalars().all()
                for product in same_cat:
                    if product.id not in seen and len(products) < limit:
                        products.append(product)
                        seen.add(product.id)
        return products


recommendation_service = RecommendationService()
