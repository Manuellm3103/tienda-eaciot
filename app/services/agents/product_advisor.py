"""Product advisor agent: recommends products from the catalog."""
import re
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.product import Product
from app.services.llm_gateway import llm_gateway
from app.services.agents.base import BaseAgent, AgentResult


STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero",
    "de", "del", "al", "a", "en", "con", "por", "para", "sin", "sobre", "entre",
    "que", "como", "cuando", "donde", "porque", "si", "no", "este", "esta", "esto",
    "ese", "esa", "eso", "mi", "tu", "su", "nos", "les", "me", "te", "lo", "le",
    "se", "ya", "muy", "mas", "más", "tengo", "quiero", "busco", "necesito",
    "regalo", "algo", "alguien", "tienes", "tenes", "tienen", "hay", "es", "son",
    "puedes", "podrias", "podrías", "recomiendame", "recomiéndame",
}


class ProductAdvisorAgent(BaseAgent):
    name = "product_advisor"

    def _extract_keywords(self, message: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", message.lower())
        return [w for w in cleaned.split() if len(w) > 2 and w not in STOPWORDS][:6]

    async def _search_products(self, db: AsyncSession, message: str, limit: int = 5) -> List[Product]:
        keywords = self._extract_keywords(message)
        if not keywords:
            result = await db.execute(
                select(Product).where(Product.is_active == True).limit(limit)
            )
            return result.scalars().all()

        conditions = []
        for word in keywords:
            conditions.append(Product.title.ilike(f"%{word}%"))
            conditions.append(Product.description.ilike(f"%{word}%"))

        query = (
            select(Product)
            .where(Product.is_active == True)
            .where(or_(*conditions))
            .limit(limit)
        )
        result = await db.execute(query)
        products = result.scalars().all()

        if not products:
            result = await db.execute(
                select(Product).where(Product.is_active == True).limit(limit)
            )
            products = result.scalars().all()
        return products

    async def run(
        self,
        db: AsyncSession,
        message: str,
        session_id: str = None,
        user_id: str = None,
        context: str = "",
    ) -> AgentResult:
        products = await self._search_products(db, message)

        context_lines = []
        for p in products:
            line = f"- {p.title}: ${float(p.price):.2f}"
            if p.description:
                line += f" — {p.description[:120]}"
            context_lines.append(line)
        catalog_context = "\n".join(context_lines) or "No hay productos disponibles."

        prompt = (
            "Eres un asesor de ventas experto de Tienda Eaciot. Responde en español de México, "
            "cercano, claro y conciso. Solo recomienda productos de la lista. No inventes.\n\n"
            f"Contexto previo de la conversación:\n{context}\n\n"
            f"Mensaje del cliente: {message}\n\n"
            f"Productos disponibles:\n{catalog_context}\n\n"
            "Responde como asesor de Tienda Eaciot:"
        )

        answer = await llm_gateway.generate(prompt)
        if not answer:
            if products:
                answer = (
                    "Encontré estos productos que pueden interesarte. "
                    "El asistente AI está cargando, pero ya puedes verlos abajo."
                )
            else:
                answer = "No encontré productos para esa búsqueda. ¿Puedes darme más detalles?"

        return AgentResult(
            answer=answer,
            agent_name=self.name,
            products=[
                {
                    "id": str(p.id),
                    "title": p.title,
                    "price": float(p.price),
                    "image_url": p.image_url,
                }
                for p in products
            ],
        )
