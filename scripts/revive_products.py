"""Reactiva productos inactivos en la base de datos de Render.

Corre desde scripts/release.sh en cada deploy, pero SOLO actúa cuando
AUTO_REVIVE_PRODUCTS=true (idempotente: activar productos ya activos es
no-op). Recupera los productos que el botón Eliminar viejo apagaba
(is_active=0) sin borrarlos.

Uso normal:  python scripts/render_deploy.py --revive-products
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import update  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models.product import Product  # noqa: E402


async def main() -> None:
    if os.getenv("AUTO_REVIVE_PRODUCTS", "").strip().lower() not in ("true", "1", "yes"):
        print("Revive: AUTO_REVIVE_PRODUCTS no está activo — nada que hacer.")
        return

    async with async_session() as db:
        result = await db.execute(
            update(Product)
            .where(Product.is_active == False)  # noqa: E712
            .values(is_active=True)
        )
        await db.commit()
        print(f"Revive: {result.rowcount} producto(s) reactivado(s) en Render.")
        print("Revive: los productos ya vuelven a salir en la tienda del comprador.")


if __name__ == "__main__":
    asyncio.run(main())
