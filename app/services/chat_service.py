"""Public chat service backed by the hierarchical AI Marketing Department.

Routes every message through the SupervisorAgent, which picks the right
specialized agent and persists conversation memory.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.agents.supervisor import SupervisorAgent


class ChatService:
    def __init__(self):
        self.supervisor = SupervisorAgent()

    async def chat(
        self,
        db: AsyncSession,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        result = await self.supervisor.run(
            db, message, session_id=session_id, user_id=user_id
        )
        return {
            "answer": result.answer,
            "agent": result.agent_name,
            "products": result.products,
            "metadata": result.metadata,
        }


chat_service = ChatService()
