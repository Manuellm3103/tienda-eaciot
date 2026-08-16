"""Content Agent for the AI Marketing Department.

Generates product copy, social media posts, and simple blog outlines by
wrapping the existing AI content pipeline.
"""
from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.base import BaseAgent, AgentResult
from app.services.product_content_service import product_content_service
from app.models.product import Product


class ContentAgent(BaseAgent):
    name = "content"

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str | None = None,
        user_id: str | None = None,
        context: str = "",
    ) -> AgentResult:
        lower = message.lower()

        # Product content enrichment
        if any(word in lower for word in ["producto", "descripción", "seo", "ficha"]):
            # Try to extract product id or name from message
            product = await self._resolve_product(db, message)
            if product:
                content = await product_content_service.generate_content(product)
                return AgentResult(
                    answer=(
                        f"Contenido generado para *{product.title}*:\n\n"
                        f"**Título SEO:** {content.get('seo_title', '')}\n\n"
                        f"**Descripción:** {content.get('description', '')}\n\n"
                        f"**Meta:** {content.get('meta_description', '')}"
                    ),
                    agent_name=self.name,
                    metadata={"product_id": str(product.id), "content": content},
                )

        # Social copy fallback
        return AgentResult(
            answer=(
                "Aquí tienes una idea de copy para redes:\n\n"
                f"'{message}' — descubre más en Tienda Eaciot. "
                "Envíos a Cuernavaca y todo México. #TiendaEaciot"
            ),
            agent_name=self.name,
        )

    async def _resolve_product(self, db: AsyncSession, message: str) -> Product | None:
        import re
        from sqlalchemy import select

        # Look for a product ID (UUID) in the message
        ids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", message, re.IGNORECASE)
        for pid in ids:
            product = await db.get(Product, pid)
            if product:
                return product

        # Otherwise fuzzy-match the first word after "producto"
        words = re.findall(r"producto\s+(.+)", message.lower())
        if words:
            term = words[0].strip()
            result = await db.execute(
                select(Product).where(Product.title.ilike(f"%{term}%")).limit(1)
            )
            return result.scalar_one_or_none()
        return None


content_agent = ContentAgent()
