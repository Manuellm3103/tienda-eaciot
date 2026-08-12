"""Supervisor agent: routes user intent to the right specialized agent.

This is the VortexOS-style hierarchical orchestrator: one coordinator
and multiple worker agents. It also persists the conversation memory.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agent_memory import agent_memory
from app.services.llm_gateway import llm_gateway
from app.services.agents.base import BaseAgent, AgentResult
from app.services.agents.product_advisor import ProductAdvisorAgent
from app.services.agents.copywriter import CopywriterAgent


class SupervisorAgent(BaseAgent):
    name = "supervisor"

    def __init__(self):
        self.product_advisor = ProductAdvisorAgent()
        self.copywriter = CopywriterAgent()

    async def _classify_intent(self, message: str) -> str:
        """Fast local classification of the user's intent."""
        lower = message.lower()
        copy_triggers = [
            "copy", "copywriting", "anuncio", "publicidad", "frase", "texto",
            "descripción", "descripcion", "marketing", "promocionar", "vender",
        ]
        if any(t in lower for t in copy_triggers):
            return "copywriter"
        return "product_advisor"

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: str = "",
    ) -> AgentResult:
        # Persist user message
        if session_id:
            await agent_memory.add_message(
                db, session_id, "user", message, agent_name=None, user_id=user_id
            )
            context = await agent_memory.get_recent_context(db, session_id)

        intent = await self._classify_intent(message)

        if intent == "copywriter":
            result = await self.copywriter.run(
                db, message, session_id=session_id, user_id=user_id, context=context
            )
        else:
            result = await self.product_advisor.run(
                db, message, session_id=session_id, user_id=user_id, context=context
            )

        # Persist assistant response
        if session_id:
            await agent_memory.add_message(
                db,
                session_id,
                "assistant",
                result.answer,
                agent_name=result.agent_name,
                user_id=user_id,
            )

        return result
