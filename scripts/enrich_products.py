"""Auto-enrich de productos con el departamento de marketing IA (best-effort).

Corre en la fase de release (Render) y en el entrypoint del contenedor
(Docker/Nixopus), después del bootstrap. Regenera el contenido SEO (título,
meta descripción, descripción persuasiva, bullets, términos de búsqueda) de
los productos que NUNCA han sido enriquecidos (content_generated_at IS NULL).

- Si no hay proveedor LLM configurado, sale 0 sin tocar nada (la tienda
  nunca se bloquea por IA).
- Si un producto falla, se registra y se continúa con el siguiente.
- Kill switch: AUTO_ENRICH=false desactiva el enriquecimiento automático.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.database import async_session, init_db  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.services.product_content_service import product_content_service  # noqa: E402

MAX_PRODUCTS = 25


async def main() -> None:
    # Auto-cura el esquema SQLite antes de tocar la BD (el release corre
    # antes que el arranque de la app en Render).
    await init_db()
    if os.getenv("AUTO_ENRICH", "true").strip().lower() in ("false", "0", "no"):
        print("Enrich: desactivado (AUTO_ENRICH=false)")
        return

    async with async_session() as db:
        products = (
            await db.execute(
                select(Product)
                .where(Product.is_active == True)  # noqa: E712
                .where(Product.content_generated_at.is_(None))
                .limit(MAX_PRODUCTS)
            )
        ).scalars().all()

        if not products:
            print("Enrich: ningún producto pendiente")
            return

        print(f"Enrich: {len(products)} productos pendientes — generando contenido IA...")
        ok = fail = 0
        for p in products:
            try:
                res = await product_content_service.apply_to_product(db, p)
                await db.commit()
                if res["status"] == "generated":
                    ok += 1
                else:
                    fail += 1
                    print(f"  {p.title[:40]}: proveedor IA no disponible")
            except Exception as exc:
                fail += 1
                await db.rollback()
                print(f"  {p.title[:40]}: error ({str(exc)[:80]})")
        print(f"Enrich: {ok} generados, {fail} sin contenido")


if __name__ == "__main__":
    asyncio.run(main())
