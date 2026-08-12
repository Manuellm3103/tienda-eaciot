"""Persistent agent memory for chat sessions.

Inspired by Agent-Span's namespaced key/value scratchpad, but mapped to
relational rows so sessions survive restarts and can be audited.
"""
from typing import List, Optional
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.chat import ChatMessage


def create_session_id() -> str:
    return str(uuid4())


class AgentMemory:
    async def add_message(
        self,
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ChatMessage:
        msg = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            agent_name=agent_name,
            user_id=user_id,
        )
        db.add(msg)
        await db.flush()
        return msg

    async def get_history(
        self, db: AsyncSession, session_id: str, limit: int = 10
    ) -> List[ChatMessage]:
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_context(
        self, db: AsyncSession, session_id: str, limit: int = 6
    ) -> str:
        """Return recent messages as a conversation string for the LLM prompt."""
        messages = await self.get_history(db, session_id, limit=limit)
        lines = []
        for m in messages:
            prefix = "Cliente" if m.role == "user" else "Asesor"
            lines.append(f"{prefix}: {m.content}")
        return "\n".join(lines)


agent_memory = AgentMemory()
