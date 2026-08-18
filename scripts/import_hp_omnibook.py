"""Importa el catálogo HP OmniBook desde scripts/data/hp_omnibook.json.

Cada producto entra como BORRADOR (is_active=False, precio 0 = pendiente del
dueño). Los campos cost_price (precio en que lo consigue) y hp_price (precio
de la página oficial HP) son INTERNOS: solo visibles en el admin, nunca en la
tienda pública.

- Idempotente: solo crea productos cuyo título no existe ya.
- Media: image_url y videos apuntan SIEMPRE a contenido directo de HP
  (CDN oficial hp.widen.net, hp.com). Nada de resellers ni reviews de terceros.
- Corre desde entrypoint.sh en Render; se activa con IMPORT_HP=true
  (ya configurado en render.env).
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

from app.database import async_session, init_db  # noqa: E402
from app.models.product import Product, Category  # noqa: E402

CATALOG = REPO / "scripts" / "data" / "hp_omnibook.json"


async def main() -> None:
    # Auto-cura el esquema SQLite ANTES de tocar la BD (igual que
    # restore_catalog): en Render el release corre antes del arranque de la app.
    await init_db()
    if os.getenv("IMPORT_HP", "").strip().lower() not in ("true", "1", "yes"):
        print("HP: IMPORT_HP no está activo — nada que hacer.")
        return
    if not CATALOG.exists():
        print("HP: no existe scripts/data/hp_omnibook.json — nada que importar.")
        return

    items = json.loads(CATALOG.read_text(encoding="utf-8"))
    async with async_session() as db:
        creados = 0
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

            specs = dict(it.get("specs") or {})
            if it.get("hp_price_currency"):
                specs["_hp_precio_moneda"] = it["hp_price_currency"]

            product = Product(
                title=it["title"],
                description=it.get("description") or None,
                price=Decimal(str(it.get("price", "0.00"))),
                product_type=it.get("product_type", "fisico"),
                stock=int(it.get("stock", 1)),
                category_id=cat.id,
                is_active=bool(it.get("is_active", False)),
                image_url=it.get("image_url") or None,
                specs=specs,
                videos=it.get("videos") or None,
                # Internos (solo admin):
                cost_price=(
                    Decimal(str(it["cost_price"])) if it.get("cost_price") else None
                ),
                hp_price=(
                    Decimal(str(it["hp_price"])) if it.get("hp_price") else None
                ),
            )
            db.add(product)
            await db.flush()
            creados += 1
        await db.commit()
        print(f"HP: {creados} productos OmniBook creados como borradores "
              f"(precio pendiente del dueño, inactivos).")


if __name__ == "__main__":
    asyncio.run(main())
