from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from typing import Dict, List
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.promotion import Promotion
from app.ai.customer_analyzer import customer_analyzer
from app.ai.promotion_generator import promotion_generator

PENDING_ORDER_STATUSES = ("pending", "processing")


def _sparkline_points(values: List[float], width: int = 100, height: int = 32) -> str:
    """Convierte una serie en puntos de un <polyline> SVG (sparkline inline).

    Devuelve una cadena "x,y x,y ..." lista para usar en el atributo `points`.
    Si todos los valores son iguales, dibuja una línea plana centrada.
    """
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = (mx - mn) or 1.0
    n = len(values)
    step = (width / (n - 1)) if n > 1 else 0.0
    pts = []
    for i, v in enumerate(values):
        x = i * step
        y = height - 4 - ((v - mn) / rng) * (height - 8)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


class DashboardService:
    async def get_dashboard_metrics(self, db: AsyncSession) -> dict:
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)

        # ── Ventas ──────────────────────────────────────────────────────────
        total_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(Order.status == "paid")
        )
        today_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(
                and_(Order.status == "paid", func.date(Order.created_at) == today)
            )
        )
        week_sales = await db.execute(
            select(func.sum(Order.total_amount)).where(
                and_(Order.status == "paid", Order.created_at >= week_ago)
            )
        )
        paid_count = await db.execute(
            select(func.count(Order.id)).where(Order.status == "paid")
        )
        total_sales_v = float(total_sales.scalar() or 0)
        paid_count_v = int(paid_count.scalar() or 0)

        # Tendencia de ventas últimos 7 días (para sparkline)
        sales_trend: List[float] = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            nxt = day + timedelta(days=1)
            row = await db.execute(
                select(func.coalesce(func.sum(Order.total_amount), 0)).where(
                    and_(Order.status == "paid", Order.created_at >= day, Order.created_at < nxt)
                )
            )
            sales_trend.append(float(row.scalar() or 0))

        # ── Pedidos ─────────────────────────────────────────────────────────
        pending_count = await db.execute(
            select(func.count(Order.id)).where(Order.status.in_(PENDING_ORDER_STATUSES))
        )
        recent_rows = await db.execute(
            select(Order, User.name.label("customer_name"))
            .join(User, User.id == Order.user_id)
            .order_by(Order.created_at.desc())
            .limit(5)
        )
        recent_orders = [
            {
                "id": str(o.id)[:8],
                "customer": (name or "—"),
                "total": float(o.total_amount),
                "status": o.status,
                "created_at": o.created_at,
            }
            for o, name in recent_rows.all()
        ]

        # ── Clientes ────────────────────────────────────────────────────────
        total_customers = await db.execute(select(func.count(User.id)))
        new_today = await db.execute(
            select(func.count(User.id)).where(func.date(User.created_at) == today)
        )
        customers_trend: List[int] = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            nxt = day + timedelta(days=1)
            row = await db.execute(
                select(func.count(User.id)).where(
                    and_(User.created_at >= day, User.created_at < nxt)
                )
            )
            customers_trend.append(int(row.scalar() or 0))

        loyalty_dist = await db.execute(
            select(User.loyalty_level, func.count(User.id)).group_by(User.loyalty_level)
        )

        # ── Top productos ───────────────────────────────────────────────────
        top_products = await db.execute(
            select(Product.title, func.sum(OrderItem.quantity).label("total_sold"))
            .join(OrderItem, Product.id == OrderItem.product_id)
            .group_by(Product.title)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(10)
        )

        # ── Inventario: stock bajo ──────────────────────────────────────────
        # stock == -1 es el centinela de "producto digital/sin inventario";
        # reorder_point == 0 significa "sin alerta configurada". Ambos se
        # excluyen para no marcar todo el catálogo como agotado.
        low_rows = await db.execute(
            select(Product)
            .where(
                and_(
                    Product.reorder_point > 0,
                    Product.stock >= 0,
                    Product.stock <= Product.reorder_point,
                )
            )
            .order_by((Product.stock - Product.reorder_point).asc())
        )
        low_products = low_rows.scalars().all()
        low_stock = [
            {
                "id": str(p.id),
                "title": p.title,
                "stock": p.stock,
                "reorder_point": p.reorder_point,
            }
            for p in low_products[:5]
        ]

        # ── Estado de contenido SEO (depto marketing) ───────────────────────
        active_total = await db.execute(
            select(func.count(Product.id)).where(Product.is_active == True)  # noqa: E712
        )
        active_enriched = await db.execute(
            select(func.count(Product.id)).where(
                and_(
                    Product.is_active == True,  # noqa: E712
                    Product.content_generated_at.isnot(None),
                )
            )
        )
        content_total = int(active_total.scalar() or 0)
        content_enriched = int(active_enriched.scalar() or 0)

        return {
            "sales": {
                "total": total_sales_v,
                "today": float(today_sales.scalar() or 0),
                "this_week": float(week_sales.scalar() or 0),
                "average_order_value": (
                    round(total_sales_v / paid_count_v, 2) if paid_count_v else 0.0
                ),
                "trend_7d": sales_trend,
            },
            "orders": {
                "pending": int(pending_count.scalar() or 0),
                "recent": recent_orders,
            },
            "customers": {
                "total": total_customers.scalar() or 0,
                "new_today": new_today.scalar() or 0,
                "trend_7d": customers_trend,
                "loyalty_distribution": {row[0]: row[1] for row in loyalty_dist.all()},
            },
            "top_products": [
                {"title": row[0], "sold": row[1]} for row in top_products.all()
            ],
            "inventory": {
                "low_stock": low_stock,
                "low_stock_count": len(low_products),
            },
            "content": {
                "enriched": content_enriched,
                "pending": content_total - content_enriched,
                "total": content_total,
            },
            "sparklines": {
                "sales": _sparkline_points(sales_trend),
                "customers": _sparkline_points([float(v) for v in customers_trend]),
            },
        }

    async def get_ai_suggestions(self, db: AsyncSession) -> dict:
        # Get customer data for analysis
        customers = await db.execute(
            select(User).where(User.purchase_count > 0).limit(100)
        )
        customer_list = [
            {
                "id": str(c.id),
                "name": c.name,
                "total_spent": float(c.total_spent),
                "purchase_count": c.purchase_count,
                "loyalty_level": c.loyalty_level,
                "last_purchase": str(c.last_purchase_at) if c.last_purchase_at else None,
            }
            for c in customers.scalars().all()
        ]

        # Get sales data
        sales_data = await self.get_dashboard_metrics(db)

        # Get AI suggestions
        fidel_customers = await customer_analyzer.identify_fidel_customers(customer_list)
        promo_suggestions = await promotion_generator.suggest_promotion(
            sales_data["sales"],
            sales_data["customers"]["loyalty_distribution"],
        )

        return {
            "fidel_customers": fidel_customers,
            "promotion_suggestions": promo_suggestions.get("suggestions", []),
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }

    async def approve_suggestion(self, db: AsyncSession, suggestion_type: str, suggestion_data: dict) -> dict:
        if suggestion_type == "promotion":
            promotion = Promotion(
                title=suggestion_data["title"],
                description=suggestion_data.get("description"),
                discount_type=suggestion_data["discount_type"],
                discount_value=suggestion_data["discount_value"],
                is_approved=True,
                ai_suggestion=suggestion_data,
            )
            db.add(promotion)
            await db.flush()
            return {"status": "approved", "id": str(promotion.id)}

        return {"status": "unknown_type"}


dashboard_service = DashboardService()
