"""AI product content generation (#6 on the innovation roadmap).

Generates a complete SEO package (SEO title, meta description, persuasive
description, bullet points, Mexican search terms, alt texts) and scores it
through the dual-LLM router.

Fallo controlado: si el LLM no está configurado o no responde, cae a un
catálogo de contenido SEO PRE-generado (scripts/data/enriched_content.json)
para que el botón "Generar Contenido IA" siempre deje el producto listo.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.product import Product
from app.ai.llm_router import llm_router, TaskType
from app.services.app_setting_service import get_setting

SYSTEM_PROMPT = (
    "Eres un especialista SEO de comercio electrónico para Tienda Eaciot, "
    "una tienda mexicana. Escribes en español de México con un tono cercano y "
    "persuasivo, optimizado para búsquedas locales. Responde SIEMPRE con JSON "
    "válido, sin comentarios ni markdown."
)

# Catálogo offline (cargado una vez, en memoria).
_OFFLINE_CATALOG: Optional[dict] = None


def _load_offline_catalog() -> dict:
    global _OFFLINE_CATALOG
    if _OFFLINE_CATALOG is not None:
        return _OFFLINE_CATALOG
    path = Path(__file__).resolve().parents[2] / "scripts" / "data" / "enriched_content.json"
    try:
        _OFFLINE_CATALOG = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _OFFLINE_CATALOG = {}
    return _OFFLINE_CATALOG


class ProductContentService:
    async def _selected_llm(self, db: AsyncSession) -> tuple[str, str]:
        """(provider, model) elegidos por el admin, o ('', '') para usar la ruta por defecto."""
        provider = (await get_setting(db, "llm_provider", "")).strip()
        model = (await get_setting(db, "llm_model", "")).strip()
        return provider, model

    async def generate_content(self, product: Product, provider: str = "", model: str = "") -> dict:
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
            prompt,
            system=SYSTEM_PROMPT,
            task_type=TaskType.PRODUCT_DESCRIPTION,
            force_provider=provider or None,
            model=model or None,
        )

    def _score_content(self, content: dict) -> tuple[float, float]:
        """Return (content_score, seo_score) between 0 and 100."""
        # Acepta 'seo_title' (salida del LLM) o 'meta_title' (catálogo offline).
        seo_title = content.get("seo_title") or content.get("meta_title")
        seo_checks = [
            bool(seo_title and len(str(seo_title)) <= 60),
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

    @staticmethod
    def _is_usable(content: dict) -> bool:
        return any(
            content.get(k) for k in ("seo_title", "meta_title", "meta_description", "description")
        )

    def _lookup_offline(self, title: str) -> Optional[dict]:
        entry = _load_offline_catalog().get(title)
        if not entry:
            return None
        content = dict(entry)
        if not content.get("seo_title") and content.get("meta_title"):
            content["seo_title"] = content["meta_title"]
        return content

    async def _persist_content(self, db: AsyncSession, product: Product, content: dict, source: str) -> dict:
        """Aplica un dict de contenido SEO al producto y lo puntúa."""
        seo_title = content.get("seo_title") or content.get("meta_title")
        if seo_title:
            product.meta_title = str(seo_title)[:255]
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
            "source": source,
            "content": content,
            "content_score": content_score,
            "seo_score": seo_score,
        }

    async def apply_to_product(self, db: AsyncSession, product: Product) -> dict:
        """Generate and persist SEO content + scores onto Product columns.

        Fallback offline: si el LLM no produce contenido usable, usa el catálogo
        pre-generado (por título exacto) para no dejar el botón colgado.
        """
        provider, model = await self._selected_llm(db)
        content = await self.generate_content(product, provider, model)
        if self._is_usable(content):
            return await self._persist_content(db, product, content, source="llm")

        offline = self._lookup_offline(product.title)
        if offline:
            return await self._persist_content(db, product, offline, source="offline")

        return {"status": "unavailable", "content": content}

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
        by_llm = 0
        by_offline = 0
        for p in products:
            if not force and p.description and len(p.description) >= 50:
                continue
            if enriched >= limit:
                break
            res = await self.apply_to_product(db, p)
            if res["status"] == "generated":
                enriched += 1
                if res.get("source") == "offline":
                    by_offline += 1
                else:
                    by_llm += 1
            else:
                failed += 1
        return {
            "enriched": enriched,
            "failed": failed,
            "llm": by_llm,
            "offline": by_offline,
        }


product_content_service = ProductContentService()
