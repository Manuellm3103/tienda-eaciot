"""AI smart bundle engine: discover product affinities from orders.

Mines co-purchase patterns and generates bundle discounts such as
"Frecuentemente comprados juntos con 15% de descuento".
"""
from collections import defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.order import OrderItem
from app.models.product import Product
from app.models.product_bundle import ProductBundle


class BundleService:
    """Mine order history to discover and recommend product bundles."""

    async def mine_bundles(
        self,
        db: AsyncSession,
        min_support: int = 2,
        max_bundle_size: int = 3,
    ) -> list[dict[str, Any]]:
        """Find product sets frequently bought together.

        Returns candidate bundles with support (co-occurrence count) and lift.
        """
        result = await db.execute(
            select(OrderItem.order_id, OrderItem.product_id)
            .order_by(OrderItem.order_id)
        )
        rows = result.all()

        orders: dict[str, set[str]] = defaultdict(set)
        for order_id, product_id in rows:
            orders[order_id].add(product_id)

        # Count product frequencies
        product_counts: dict[str, int] = defaultdict(int)
        for items in orders.values():
            for pid in items:
                product_counts[pid] += 1

        # Count pair/triplet frequencies
        pair_counts: dict[tuple[str, ...], int] = defaultdict(int)
        triplet_counts: dict[tuple[str, ...], int] = defaultdict(int)

        for items in orders.values():
            sorted_items = sorted(items)
            n = len(sorted_items)
            if n < 2:
                continue
            for i in range(n):
                for j in range(i + 1, n):
                    pair = (sorted_items[i], sorted_items[j])
                    pair_counts[pair] += 1
                    if max_bundle_size >= 3:
                        for k in range(j + 1, n):
                            triplet = (sorted_items[i], sorted_items[j], sorted_items[k])
                            triplet_counts[triplet] += 1

        candidates: list[dict[str, Any]] = []
        total_orders = len(orders)
        if total_orders == 0:
            return candidates

        for pair, count in pair_counts.items():
            if count < min_support:
                continue
            a, b = pair
            support_a = product_counts[a] / total_orders
            support_b = product_counts[b] / total_orders
            support_pair = count / total_orders
            lift = support_pair / (support_a * support_b) if support_a and support_b else 0
            candidates.append({
                "product_ids": list(pair),
                "support": count,
                "lift": round(lift, 2),
                "confidence": round(count / product_counts[a], 2),
            })

        for triplet, count in triplet_counts.items():
            if count < min_support:
                continue
            a, b, c = triplet
            support_a = product_counts[a] / total_orders
            support_b = product_counts[b] / total_orders
            support_c = product_counts[c] / total_orders
            denom = support_a * support_b * support_c
            lift = (count / total_orders) / denom if denom else 0
            candidates.append({
                "product_ids": list(triplet),
                "support": count,
                "lift": round(lift, 2),
                "confidence": round(count / product_counts[a], 2),
            })

        # Sort by support desc, then lift desc
        candidates.sort(key=lambda x: (-x["support"], -x["lift"]))
        return candidates

    async def generate_bundles(
        self,
        db: AsyncSession,
        min_support: int = 2,
        discount_percentage: float = 15.0,
    ) -> list[ProductBundle]:
        """Generate ProductBundle records from mined affinities."""
        candidates = await self.mine_bundles(db, min_support=min_support)
        bundles: list[ProductBundle] = []

        for candidate in candidates[:20]:  # top 20
            # Fetch product names for bundle name
            result = await db.execute(
                select(Product.id, Product.title)
                .where(Product.id.in_(candidate["product_ids"]))
            )
            titles = {row.id: row.title for row in result.all()}
            names = [titles.get(pid, "Producto") for pid in candidate["product_ids"]]
            name = " + ".join(names[:2]) + (" y más" if len(names) > 2 else "")

            bundle = ProductBundle(
                name=f"Combo {name}",
                product_ids=candidate["product_ids"],
                discount_type="percentage",
                discount_value=discount_percentage,
                score=min(1.0, candidate["lift"] / 5.0) if candidate["lift"] else 0.5,
                ai_generated=True,
                is_active=True,
            )
            db.add(bundle)
            bundles.append(bundle)

        await db.flush()
        return bundles

    async def get_bundles_for_product(
        self,
        db: AsyncSession,
        product_id: str,
    ) -> list[ProductBundle]:
        """Return active bundles containing a given product."""
        result = await db.execute(
            select(ProductBundle)
            .where(ProductBundle.is_active == True)
        )
        all_bundles = result.scalars().all()
        return [b for b in all_bundles if product_id in b.product_ids]

    async def calculate_bundle_price(
        self,
        db: AsyncSession,
        bundle: ProductBundle,
    ) -> dict[str, Any]:
        """Calculate total and discounted price for a bundle."""
        result = await db.execute(
            select(Product.id, Product.price)
            .where(Product.id.in_(bundle.product_ids))
        )
        prices = {row.id: float(row.price) for row in result.all()}
        total = sum(prices.get(pid, 0) for pid in bundle.product_ids)

        discount = 0.0
        if bundle.discount_type == "percentage":
            discount = total * (float(bundle.discount_value) / 100)
        elif bundle.discount_type == "fixed":
            discount = float(bundle.discount_value)

        final = max(0.0, total - discount)
        return {
            "original_price": round(total, 2),
            "discount": round(discount, 2),
            "final_price": round(final, 2),
        }


bundle_service = BundleService()
