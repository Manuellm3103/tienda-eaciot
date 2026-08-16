"""Marketing Orchestrator for the AI Marketing Department (#5).

Routes marketing-related tasks to specialized agents (content, SEO, campaign,
analytics) and persists every decision to the marketing_decisions table.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.marketing_decision import MarketingDecision
from app.services.agents.base import BaseAgent, AgentResult
from app.services.agents.content_agent import content_agent
from app.services.agents.seo_agent import seo_agent
from app.services.agents.campaign_agent import campaign_agent
from app.services.agents.analytics_agent import analytics_agent


class MarketingOrchestrator(BaseAgent):
    name = "marketing_orchestrator"

    def __init__(self):
        self.content = content_agent
        self.seo = seo_agent
        self.campaign = campaign_agent
        self.analytics = analytics_agent

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        context: str = "",
    ) -> AgentResult:
        task_type = self._classify(message)

        decision = MarketingDecision(
            agent_id=self.name,
            task_type=task_type,
            decision=message,
            context={"session_id": session_id, "user_id": user_id},
        )
        db.add(decision)
        await db.flush()

        if task_type == "content":
            result = await self.content.run(db, message, session_id, user_id, context)
        elif task_type == "seo":
            result = await self.seo.run(db, message, session_id, user_id, context)
        elif task_type == "campaign":
            result = await self.campaign.run(db, message, session_id, user_id, context)
        elif task_type == "analytics":
            result = await self.analytics.run(db, message, session_id, user_id, context)
        else:
            result = AgentResult(
                answer="No entendí el tipo de tarea de marketing. Prueba con 'genera contenido', 'keywords', 'campaña' o 'reporte'.",
                agent_name=self.name,
            )

        decision.outcome = result.answer[:500]
        await db.flush()
        return result

    def _classify(self, message: str) -> str:
        lower = message.lower()
        if any(w in lower for w in ["contenido", "descripción", "copy", "blog", "publicación", "redes", "producto"]):
            return "content"
        if any(w in lower for w in ["seo", "keyword", "palabra clave", "meta", "términos", "terminos"]):
            return "seo"
        if any(w in lower for w in ["campaña", "campa�a", "email", "promoción", "promocion", "navidad", "buen fin", "cumpleaños"]):
            return "campaign"
        if any(w in lower for w in ["reporte", "métricas", "metricas", "ventas", "analytics", "kpi"]):
            return "analytics"
        return "unknown"


marketing_orchestrator = MarketingOrchestrator()
