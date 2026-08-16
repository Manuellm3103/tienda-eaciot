"""AI Inventory & Restock Prediction (#4.3 on the innovation roadmap).

Predicts stock-out dates and recommends reorder quantities using a simple
statistical forecaster. If `statsforecast` is available we use `AutoARIMA` with
weekly seasonality; otherwise a rule-based rolling-average fallback is used.

Mexican holiday boosts are applied to the forecast around known retail events.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem
from app.models.product import Product


MEXICAN_HOLIDAYS: dict[str, date] = {
    "buen_fin": date(2025, 11, 14),
    "dia_muertos": date(2025, 11, 2),
    "navidad": date(2025, 12, 25),
    "reyes_magos": date(2026, 1, 6),
    "san_valentin": date(2026, 2, 14),
    "dia_nino": date(2026, 4, 30),
    "dia_madre": date(2026, 5, 10),
    "hot_sale": date(2026, 5, 26),
}

# Boost multiplier applied to the forecast on the holiday week.
HOLIDAY_BOOST = 1.5


class InventoryForecaster:
    MIN_DAYS_FOR_FORECAST = 7
    DEFAULT_FORECAST_HORIZON = 30

    async def predict_stockout(
        self, db: AsyncSession, product_id: str
    ) -> dict[str, Any]:
        """Predict when a product will run out of stock and how much to reorder."""
        product = await db.get(Product, product_id)
        if not product:
            raise ValueError("Product not found")

        stock = product.stock if product.stock is not None else -1
        if stock < 0:
            return {
                "days_until_stockout": None,
                "predicted_date": None,
                "restock_recommendation": 0,
                "confidence": "low",
                "reason": "Stock ilimitado",
            }

        history = await self._get_daily_sales(db, product_id, days=90)
        if len(history) < self.MIN_DAYS_FOR_FORECAST:
            return {
                "days_until_stockout": None,
                "predicted_date": None,
                "restock_recommendation": 0,
                "confidence": "low",
                "reason": f"Solo {len(history)} días de historial de ventas",
            }

        forecast = await self._forecast_demand(history, horizon=self.DEFAULT_FORECAST_HORIZON)
        cumulative = 0.0
        days_until = None
        for day_idx, value in enumerate(forecast, start=1):
            cumulative += value
            if cumulative >= stock:
                days_until = day_idx
                break

        safety_days = product.safety_stock_days or 7
        safety_stock = forecast[:safety_days] if len(forecast) >= safety_days else forecast
        safety_units = sum(safety_stock) if safety_stock else 0.0

        restock = 0
        if days_until is not None:
            # Recommend enough to cover the forecast horizon plus safety stock.
            restock = max(0, int(sum(forecast) + safety_units - stock))
        elif stock <= (product.reorder_point or 0):
            restock = int(sum(forecast) + safety_units)

        predicted_date: date | None = None
        if days_until is not None:
            predicted_date = date.today() + timedelta(days=days_until)

        confidence = "high" if len(history) >= 60 else "medium"
        return {
            "days_until_stockout": days_until,
            "predicted_date": predicted_date.isoformat() if predicted_date else None,
            "restock_recommendation": restock,
            "confidence": confidence,
            "forecast_next_30d": round(sum(forecast), 2),
            "current_stock": stock,
        }

    async def _get_daily_sales(
        self, db: AsyncSession, product_id: str, days: int = 90
    ) -> list[tuple[date, float]]:
        """Return a list of (date, units_sold) for the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(
                func.date(Order.created_at).label("sale_date"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("units"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(OrderItem.product_id == product_id)
            .where(Order.status == "paid")
            .where(Order.created_at >= since)
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
        result = await db.execute(stmt)
        rows = result.all()
        parsed: list[tuple[date, float]] = []
        for row in rows:
            if not row.sale_date:
                continue
            sale_date = row.sale_date
            if isinstance(sale_date, str):
                sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
            parsed.append((sale_date, float(row.units)))
        return parsed

    async def _forecast_demand(
        self, history: list[tuple[date, float]], horizon: int = 30
    ) -> list[float]:
        """Forecast daily demand for the next `horizon` days."""
        # Build a dense daily series starting today backwards.
        end = date.today()
        start = end - timedelta(days=89)
        history_dict = {row[0]: row[1] for row in history}
        series = [float(history_dict.get(start + timedelta(days=i), 0.0)) for i in range(90)]

        try:
            from statsforecast import StatsForecast
            from statsforecast.models import AutoARIMA

            df = {
                "ds": [end - timedelta(days=89 - i) for i in range(90)],
                "y": series,
                "unique_id": "product",
            }
            sf = StatsForecast(models=[AutoARIMA(season_length=7)], freq="D")
            sf.fit(df)
            pred = sf.predict(h=horizon)
            values = [float(pred["AutoARIMA"].iloc[i]) for i in range(horizon)]
        except Exception:
            # Fallback: 14-day rolling average, padded with zeros if needed.
            window = series[-14:] if len(series) >= 14 else series
            avg = sum(window) / len(window) if window else 0.0
            values = [max(0.0, avg)] * horizon

        # Apply holiday boost
        boosted: list[float] = []
        for i, value in enumerate(values, start=1):
            forecast_date = end + timedelta(days=i)
            boosted_value = value
            for holiday in MEXICAN_HOLIDAYS.values():
                if abs((forecast_date - holiday).days) <= 3:
                    boosted_value *= HOLIDAY_BOOST
                    break
            boosted.append(round(max(0.0, boosted_value), 2))
        return boosted

    async def get_low_stock_products(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Return products that are at or below reorder point or predicted to stock out."""
        result = await db.execute(select(Product).where(Product.stock >= 0))
        products = result.scalars().all()
        low_stock: list[dict[str, Any]] = []
        for product in products:
            prediction = await self.predict_stockout(db, str(product.id))
            if (
                product.stock <= (product.reorder_point or 0)
                or (prediction["days_until_stockout"] is not None and prediction["days_until_stockout"] <= 14)
            ):
                low_stock.append(
                    {
                        "product_id": str(product.id),
                        "title": product.title,
                        "stock": product.stock,
                        "reorder_point": product.reorder_point,
                        "days_until_stockout": prediction["days_until_stockout"],
                        "predicted_date": prediction["predicted_date"],
                        "restock_recommendation": prediction["restock_recommendation"],
                        "confidence": prediction["confidence"],
                    }
                )
        return low_stock


inventory_forecaster = InventoryForecaster()
