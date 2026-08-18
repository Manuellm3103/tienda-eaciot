"""Restaura el catálogo de laptops/SSD desde scripts/data/catalogo.json.

Corre desde scripts/release.sh SOLO cuando RESTORE_CATALOG=true (mismo patrón
que AUTO_REVIVE_PRODUCTS). Es idempotente: solo crea productos cuyo título no
existe ya. Después de crearlos, el depto de marketing IA los enriquece
(best-effort: sin IA el producto se publica con la descripción base).

Edita scripts/data/catalogo.json con tus modelos y precios reales antes de
correr:  python scripts/render_deploy.py --restore-catalog
"""
import asyncio
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from sqlalchemy import select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models.product import Product, Category  # noqa: E402
from app.services.product_content_service import product_content_service  # noqa: E402

CATALOG = REPO / "scripts" / "data" / "catalogo.json"


async def main() -> None:
    if os.getenv("RESTORE_CATALOG", "").strip().lower() not in ("true", "1", "yes"):
        print("Restore: RESTORE_CATALOG no está activo — nada que hacer.")
        return
    if not CATALOG.exists():
        print("Restore: no existe scripts/data/catalogo.json — nada que restaurar.")
        return

    items = json.loads(CATALOG.read_text(encoding="utf-8"))
    async with async_session() as db:
        creados = 0
        enriquecidos = 0
        for it in items:
            exists = (
                await db.execute(select(Product).where(Product.title == it["title"]))
            ).scalar_one_or_none()
            if exists:
                continue

            slug = it.get("category", "general")
            cat = (await db.execute(select(Category).where(Category.slug == slug))).scalar_one_or_none()
            if not cat:
                cat = Category(name=slug.capitalize(), slug=slug)
                db.add(cat)
                await db.flush()

            product = Product(
                title=it["title"],
                description=it.get("description") or None,
                price=Decimal(str(it["price"])),
                product_type=it.get("product_type", "fisico"),
                stock=int(it.get("stock", 10)),
                category_id=cat.id,
                compare_at_price=(
                    Decimal(str(it["compare_at_price"]))
                    if it.get("compare_at_price")
                    else None
                ),
            )
            db.add(product)
            await db.flush()
            creados += 1
            try:
                res = await product_content_service.apply_to_product(db, product)
                if res["status"] == "generated":
                    enriquecidos += 1
            except Exception:
                pass
        await db.commit()
        print(f"Restore: {creados} productos creados, {enriquecidos} enriquecidos con IA.")


if __name__ == "__main__":
    asyncio.run(main())
