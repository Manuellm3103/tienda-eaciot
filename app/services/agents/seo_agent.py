"""SEO Agent for the AI Marketing Department.

Suggests keywords, search terms, and meta optimizations by inspecting the
catalog and existing search queries.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base import BaseAgent, AgentResult
from app.models.product import Product


class SEOAgent(BaseAgent):
    name = "seo"

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        context: str = "",
    ) -> AgentResult:
        lower = message.lower()

        if any(word in lower for word in ["keyword", "palabra clave", "términos", "terminos", "seo"]):
            result = await db.execute(
                select(Product.title)
                .where(Product.is_active == True)
                .order_by(func.random())
                .limit(10)
            )
            titles = [row[0] for row in result.all() if row[0]]

            keywords = set()
            for title in titles:
                for word in title.lower().split():
                    if len(word) > 3:
                        keywords.add(word)
            suggestions = sorted(keywords)[:15]

            return AgentResult(
                answer=(
                    "Sugerencias de términos de búsqueda basadas en tu catálogo:\n\n"
                    + "\n".join(f"- {kw}" for kw in suggestions)
                    + "\n\nRecomendación: incluye estos términos en títulos, meta descripciones y alt text."
                ),
                agent_name=self.name,
                metadata={"suggested_keywords": suggestions},
            )

        return AgentResult(
            answer="Puedo ayudarte con keywords, meta descripciones y optimización SEO. ¿Sobre qué producto quieres trabajar?",
            agent_name=self.name,
        )


seo_agent = SEOAgent()
