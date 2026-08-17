"""AI product content generation (#6 on the innovation roadmap).

Generates a complete SEO package (SEO title, meta description, persuasive
description, bullet points, Mexican search terms, alt texts) and scores it
through the dual-LLM router.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.ai.llm_router import llm_router, TaskType

SYSTEM_PROMPT = (
    "Eres un especialista SEO de comercio electrónico para Tienda Eaciot, "
    "una tienda mexicana. Escribes en español de México con un tono cercano y "
    "persuasivo, optimizado para búsquedas locales. Responde SIEMPRE con JSON "
    "válido, sin comentarios ni markdown."
)


class ProductContentService:
    async def generate_content(self, product: Product) -> dict:
        prompt = (
            f"Genera el contenido SEO completo para este producto:\n"
            f"Título: {product.title}\n"
            f"Descripción actual: {product.description or 'Ninguna'}\n"
            f"Precio: ${float(product.price):.2f}\n\n"
            "Devuelve un JSON con exactamente estas claves:\n"
            '{"seo_title": "...", "meta_description": "...", "description": "...", '
            '"bullet_points": ["...", "..."], "search_terms": ["...", "..."], '
            '"alt_texts": ["...", "..."]}\n\n'
            "Reglas:\n"
            "- seo_title: máximo 60 caracteres, incluye palabra clave principal.\n"
            "- meta_description: máximo 155 caracteres, con gancho comercial.\n"
            "- description: entre 80 y 180 palabras, persuasiva, en español de México.\n"
            "- bullet_points: entre 3 y 5 beneficios concretos.\n"
            "- search_terms: entre 5 y 8 términos de búsqueda mexicanos.\n"
            "- alt_texts: entre 2 y 4 textos alternativos descriptivos para imágenes."
        )
        return await llm_router.generate_structured(
            prompt, system=SYSTEM_PROMPT, task_type=TaskType.PRODUCT_DESCRIPTION
        )

    def _score_content(self, content: dict) -> tuple[float, float]:
        """Return (content_score, seo_score) between 0 and 100."""
        seo_checks = [
            bool(content.get("seo_title") and len(str(content["seo_title"])) <= 60),
            bool(content.get("meta_description") and len(str(content["meta_description"])) <= 155),
            bool(content.get("description") and 80 <= len(str(content["description"]).split()) <= 180),
            bool(content.get("search_terms") and isinstance(content["search_terms"], list) and len(content["search_terms"]) >= 5),
        ]
        content_checks = [
            bool(content.get("description") and len(str(content["description"])) >= 200),
            bool(content.get("bullet_points") and isinstance(content["bullet_points"], list) and len(content["bullet_points"]) >= 3),
            bool(content.get("alt_texts") and isinstance(content["alt_texts"], list) and len(content["alt_texts"]) >= 2),
        ]
        seo_score = sum(seo_checks) / len(seo_checks) * 100 if seo_checks else 0.0
        content_score = sum(content_checks) / len(content_checks) * 100 if content_checks else 0.0
        return round(content_score, 2), round(seo_score, 2)

    async def apply_to_product(self, db: AsyncSession, product: Product) -> dict:
        """Generate and persist SEO content + scores onto Product columns."""
        content = await self.generate_content(product)
        usable = any(
            content.get(k) for k in ("seo_title", "meta_description", "description")
        )
        if not usable:
            return {"status": "unavailable", "content": content}

        if content.get("seo_title"):
            product.meta_title = str(content["seo_title"])[:255]
        if content.get("meta_description"):
            product.meta_description = str(content["meta_description"])[:500]
        if content.get("description"):
            product.description = str(content["description"])

        alt_texts = content.get("alt_texts")
        if isinstance(alt_texts, list):
            product.alt_texts = [str(x) for x in alt_texts]

        content_score, seo_score = self._score_content(content)
        product.content_score = content_score
        product.seo_score = seo_score
        product.content_generated_at = datetime.utcnow()

        await db.flush()
        return {
            "status": "generated",
            "content": content,
            "content_score": content_score,
            "seo_score": seo_score,
        }

    async def batch_enrich(self, db: AsyncSession, limit: int = 20, force: bool = False) -> dict:
        """Enrich active products.

        force=False: solo productos sin descripción o con descripción corta.
        force=True: reescribe TODOS los productos activos (lo que pide el
        dueño cuando quiere que el depto de marketing refresque el catálogo).
        """
        result = await db.execute(
            select(Product).where(Product.is_active == True)
        )
        products = result.scalars().all()

        enriched = 0
        failed = 0
        for p in products:
            if not force and p.description and len(p.description) >= 50:
                continue
            if enriched >= limit:
                break
            res = await self.apply_to_product(db, p)
            if res["status"] == "generated":
                enriched += 1
            else:
                failed += 1
        return {"enriched": enriched, "failed": failed}


product_content_service = ProductContentService()
