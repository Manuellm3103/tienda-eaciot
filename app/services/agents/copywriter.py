"""Copywriter agent: generates marketing copy for products."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.product import Product
from app.services.llm_gateway import llm_gateway
from app.services.agents.base import BaseAgent, AgentResult


class CopywriterAgent(BaseAgent):
    name = "copywriter"

    async def _find_product(self, db: AsyncSession, message: str) -> Product | None:
        """Heuristic: try to find a product mentioned in the message."""
        from app.services.agents.product_advisor import ProductAdvisorAgent

        keywords = ProductAdvisorAgent()._extract_keywords(message)
        if not keywords:
            return None

        conditions = []
        for word in keywords:
            conditions.append(Product.title.ilike(f"%{word}%"))
            conditions.append(Product.description.ilike(f"%{word}%"))

        result = await db.execute(
            select(Product)
            .where(Product.is_active == True)
            .where(or_(*conditions))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str = None,
        user_id: str = None,
        context: str = "",
    ) -> AgentResult:
        product = await self._find_product(db, message)

        if product:
            product_info = (
                f"Título: {product.title}\n"
                f"Precio: ${float(product.price):.2f}\n"
                f"Descripción actual: {product.description or 'Ninguna'}"
            )
        else:
            product_info = "No se especificó un producto concreto."

        prompt = (
            "Eres un copywriter creativo de Tienda Eaciot. Genera texto de marketing corto, "
            "atractivo y en español de México para el producto indicado. "
            "Devuelve un título, un bullet de beneficio principal y una frase de cierre.\n\n"
            f"Contexto previo:\n{context}\n\n"
            f"Solicitud del usuario: {message}\n\n"
            f"{product_info}\n\n"
            "Copy de marketing:"
        )

        answer = await llm_gateway.generate(prompt)
        if not answer:
            answer = (
                "El copywriter AI está descansando. "
                "Puedes intentar de nuevo en unos segundos."
            )

        products = []
        if product:
            products = [
                {
                    "id": str(product.id),
                    "title": product.title,
                    "price": float(product.price),
                    "image_url": product.image_url,
                }
            ]

        return AgentResult(answer=answer, agent_name=self.name, products=products)
