"""Proactive Engine for the AI Marketing Department.

Monitors the store every 6 hours for triggers (inventory change, cart
abandonment, etc.) and delegates recommended actions to the marketing
orchestrator. Outcomes are stored in marketing_decisions for feedback.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.marketing_decision import MarketingDecision
from app.services.agents.marketing_orchestrator import marketing_orchestrator
from app.services.inventory_forecast import inventory_forecaster
from app.services.ai_loyalty_service import ai_loyalty_service


class ProactiveEngine:
    CHECK_INTERVAL_HOURS = 6

    async def run(self, db: AsyncSession) -> list[dict[str, Any]]:
        """Evaluate all triggers and return executed actions."""
        actions: list[dict[str, Any]] = []

        # Trigger: low stock / slow-moving inventory
        low_stock = await inventory_forecaster.get_low_stock_products(db)
        for item in low_stock[:5]:
            if item["restock_recommendation"] > 0:
                result = await marketing_orchestrator.run(
                    db,
                    f"campaña de promoción para liquidar stock bajo de {item['title']}",
                )
                actions.append(
                    {
                        "trigger": "inventory_change",
                        "subject": item["title"],
                        "action": "campaign",
                        "answer": result.answer,
                    }
                )

        # Trigger: at-risk customers
        from app.models.user import User
        result = await db.execute(select(User).where(User.is_active == True))
        users = result.scalars().all()
        for user in users:
            risk = await ai_loyalty_service.predict_churn_risk(db, str(user.id))
            if risk["level"] == "high":
                offer = await ai_loyalty_service.suggest_retention_offer(db, str(user.id))
                await self._log_action(db, "customer_behavior", str(user.id), offer)
                actions.append(
                    {
                        "trigger": "customer_behavior",
                        "subject": user.email,
                        "action": "retention_offer",
                        "offer": offer,
                    }
                )

        # Trigger: upcoming Mexican holiday
        from app.services.campaign_engine import campaign_engine
        upcoming = campaign_engine.get_upcoming_holidays(days=7)
        for event, event_date in upcoming.items():
            msg = f"campaña para {event} el {event_date}"
            result = await marketing_orchestrator.run(db, msg)
            actions.append(
                {
                    "trigger": "seasonal_event",
                    "subject": event,
                    "action": "campaign",
                    "answer": result.answer,
                }
            )

        return actions

    async def _log_action(
        self, db: AsyncSession, trigger: str, subject: str, details: dict[str, Any]
    ) -> None:
        decision = MarketingDecision(
            agent_id="proactive_engine",
            task_type="proactive",
            decision=f"{trigger}: {subject}",
            context={"trigger": trigger, "subject": subject, "details": details},
        )
        db.add(decision)
        await db.flush()


proactive_engine = ProactiveEngine()
