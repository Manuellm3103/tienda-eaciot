"""Analytics Agent for the AI Marketing Department.

Produces periodic insight reports by querying store metrics and surfacing
trends without heavy BI tooling.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base import BaseAgent, AgentResult
from app.models.order import Order


class AnalyticsAgent(BaseAgent):
    name = "analytics"

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        context: str = "",
    ) -> AgentResult:
        lower = message.lower()

        if any(word in lower for word in ["métricas", "metricas", "ventas", "reporte", "analytics", "kpi"]):
            total_sales = await self._total_sales(db)
            total_orders = await self._total_orders(db)
            return AgentResult(
                answer=(
                    "Reporte rápido de la tienda:\n\n"
                    f"**Ventas totales (pagadas):** ${total_sales:,.2f}\n"
                    f"**Órdenes pagadas:** {total_orders}\n\n"
                    "Recomendación: revisa la pestaña 'Campañas IA' para activar flujos automáticos."
                ),
                agent_name=self.name,
                metadata={"total_sales": total_sales, "total_orders": total_orders},
            )

        return AgentResult(
            answer="Puedo generar reportes de ventas, productos más vendidos y KPIs. ¿Qué período te interesa?",
            agent_name=self.name,
        )

    async def _total_sales(self, db: AsyncSession) -> float:
        result = await db.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.status == "paid")
        )
        return float(result.scalar())

    async def _total_orders(self, db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count(Order.id)).where(Order.status == "paid")
        )
        return int(result.scalar())


analytics_agent = AnalyticsAgent()
