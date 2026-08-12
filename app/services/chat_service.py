"""AI shopping assistant powered by Ollama.

Provides a simple RAG-style experience: the assistant receives the user
message, retrieves relevant products from the catalog, and asks a local
Ollama model to generate a helpful Spanish answer with recommendations.
"""
import httpx
import json
import re
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.product import Product
from app.config import settings


STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero",
    "de", "del", "al", "a", "en", "con", "por", "para", "sin", "sobre", "entre",
    "que", "como", "cuando", "donde", "porque", "si", "no", "este", "esta", "esto",
    "ese", "esa", "eso", "mi", "tu", "su", "nos", "les", "me", "te", "lo", "le",
    "se", "ya", "muy", "mas", "más", "tengo", "quiero", "busco", "necesito", "para",
    "regalo", "algo", "alguien", "tienes", "tenes", "tienen", "hay", "es", "son",
    "una", "unas", "puedes", "podrias", "podrías", "recomiendame", "recomiéndame",
}


class ChatService:
    def __init__(self):
        self.ollama_host = settings.ollama_host.rstrip("/")
        self.model = settings.ollama_model

    def _extract_keywords(self, message: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s]", " ", message.lower())
        words = [w for w in cleaned.split() if len(w) > 2 and w not in STOPWORDS]
        return words[:6]

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

        # Fallback to popular/active products if no keyword match
        if not products:
            result = await db.execute(
                select(Product).where(Product.is_active == True).limit(limit)
            )
            products = result.scalars().all()
        return products

    async def _call_ollama(self, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
        except Exception as exc:
            return f"(El asistente AI no está disponible en este momento: {exc})"

    async def chat(self, db: AsyncSession, message: str) -> dict:
        products = await self._search_products(db, message)

        context_lines = []
        for p in products:
            line = (
                f"- {p.title}: ${float(p.price):.2f}"
                f"{(' — ' + p.description[:120]) if p.description else ''}"
            )
            context_lines.append(line)
        context = "\n".join(context_lines) or "No hay productos disponibles."

        prompt = (
            "Eres un asesor de ventas experto de Tienda Eaciot, una tienda en línea "
            "de productos digitales y físicos. Responde en español de México, de forma "
            "cercana, clara y concisa. Usa solo los productos listados abajo para "
            "hacer recomendaciones. Si no hay nada relevante, indícalo amablemente y "
            "pregunta más detalles. No inventes productos ni precios.\n\n"
            f"Mensaje del cliente: {message}\n\n"
            "Productos disponibles:\n"
            f"{context}\n\n"
            "Responde como asesor de Tienda Eaciot:"
        )

        answer = await self._call_ollama(prompt)

        return {
            "answer": answer,
            "products": [
                {
                    "id": str(p.id),
                    "title": p.title,
                    "price": float(p.price),
                    "image_url": p.image_url,
                }
                for p in products
            ],
        }


chat_service = ChatService()
