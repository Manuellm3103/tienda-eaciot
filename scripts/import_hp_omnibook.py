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
import shutil
import sys
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from sqlalchemy import select  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import async_session, init_db  # noqa: E402
from app.models.product import Product, Category  # noqa: E402

CATALOG = REPO / "scripts" / "data" / "hp_omnibook.json"
MEDIA_SRC = REPO / "scripts" / "data" / "hp_media"


def _sync_media() -> int:
    """Copia las imágenes oficiales HP del repo al UPLOAD_DIR (idempotente).

    Fuente: scripts/data/hp_media (commiteado). Destino: settings.upload_dir
    (/var/data/uploads en Render). Así la tienda sirve las imágenes localmente
    y no depende del CDN de HP (hp.widen.net / hp.com), que responde 503 de
    forma intermitente.
    """
    if not MEDIA_SRC.exists():
        return 0
    dest_root = Path(settings.upload_dir) / "products" / "hp"
    n = 0
    for src in sorted(MEDIA_SRC.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(MEDIA_SRC)
        dst = dest_root / rel
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            n += 1
    return n


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

    sincronizadas = _sync_media()
    print(f"HP: {sincronizadas} imágenes copiadas a {settings.upload_dir}/products/hp")

    items = json.loads(CATALOG.read_text(encoding="utf-8"))
    async with async_session() as db:
        creados = 0
        actualizados = 0
        for it in items:
            title = it["title"]
            producto = (
                await db.execute(select(Product).where(Product.title == title))
            ).scalar_one_or_none()

            if producto:
                # Migrar media de CDN remoto -> local (solo una vez). No se
                # toca image_url si el admin ya la personalizó manualmente.
                img = producto.image_url or ""
                if not img or "hp.widen.net" in img or "hp.com/ca-en/shop/media" in img:
                    producto.image_url = it.get("image_url") or None
                    actualizados += 1
                    await db.flush()
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
        print(f"HP: {creados} productos creados, {actualizados} actualizados "
              f"(media local). Borradores inactivos, precio pendiente del dueño.")


if __name__ == "__main__":
    asyncio.run(main())
