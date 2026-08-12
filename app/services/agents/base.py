"""Base class for the hierarchical AI Marketing Department agents."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class AgentResult:
    answer: str
    agent_name: str
    products: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent:
    name: str = "base"

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: str = "",
    ) -> AgentResult:
        raise NotImplementedError
