"""Aplica contenido SEO pre-generado a productos pendientes (offline-first).

El depto de marketing IA (llm_router) depende de OPENCODE_HOST/MODEL/API_KEY en
Render. Cuando no están configurados, enrich_products.py reporta
"proveedor IA no disponible" y los 25 productos se quedan sin contenido.

Este script es el plan B: aplica el contenido ya redactado y commiteado en
scripts/data/enriched_content.json (basado en las specs reales de cada
producto), sin depender de ninguna llamada LLM en el deploy.

Comportamiento:
- Idempotente: solo toca productos activos con content_generated_at IS NULL.
- Coincide por título EXACTO contra las llaves del JSON (no adivina).
- Replica el scoring de ProductContentService._score_content para que los
  reportes internos sigan funcionando igual.
- Best-effort: si falla un producto, registra y continúa; nunca bloquea la
  tienda. Kill switch: AUTO_ENRICH=false.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.database import async_session, init_db  # noqa: E402
from app.models.product import Product  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent / "data" / "enriched_content.json"


def _score_content(content: dict) -> tuple[float, float]:
    """Replica ProductContentService._score_content: (content_score, seo_score)."""
    seo_checks = [
        bool(content.get("meta_title") and len(str(content["meta_title"])) <= 60),
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


def _apply(product: Product, content: dict) -> None:
    if content.get("meta_title"):
        product.meta_title = str(content["meta_title"])[:255]
    if content.get("meta_description"):
        product.meta_description = str(content["meta_description"])[:500]
    if content.get("description"):
        product.description = str(content["description"])
    alt_texts = content.get("alt_texts")
    if isinstance(alt_texts, list):
        product.alt_texts = [str(x) for x in alt_texts]
    content_score, seo_score = _score_content(content)
    product.content_score = content_score
    product.seo_score = seo_score
    product.content_generated_at = datetime.utcnow()


async def main() -> None:
    await init_db()
    if os.getenv("AUTO_ENRICH", "true").strip().lower() in ("false", "0", "no"):
        print("EnrichLocal: desactivado (AUTO_ENRICH=false)")
        return

    if not DATA_PATH.exists():
        print("EnrichLocal: no existe scripts/data/enriched_content.json, se omite")
        return

    with DATA_PATH.open("r", encoding="utf-8") as fh:
        catalog = json.load(fh)

    async with async_session() as db:
        products = (
            await db.execute(
                select(Product)
                .where(Product.is_active == True)  # noqa: E712
                .where(Product.content_generated_at.is_(None))
            )
        ).scalars().all()

        if not products:
            print("EnrichLocal: ningún producto pendiente")
            return

        ok = no_match = fail = 0
        for p in products:
            content = catalog.get(p.title)
            if content is None:
                no_match += 1
                print(f"  {p.title[:50]}: sin contenido en JSON (se omite)")
                continue
            try:
                _apply(p, content)
                await db.commit()
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                await db.rollback()
                print(f"  {p.title[:50]}: error ({str(exc)[:80]})")
        print(f"EnrichLocal: {ok} aplicados, {no_match} sin match, {fail} errores")


if __name__ == "__main__":
    asyncio.run(main())
