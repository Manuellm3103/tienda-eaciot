import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")

from sqlalchemy import or_, select  # noqa: E402

from app.database import async_session, init_db  # noqa: E402
from app.models.product import Product  # noqa: E402


async def main() -> None:
    await init_db()
    async with async_session() as db:
        rows = (
            await db.execute(
                select(Product).where(
                    or_(
                        Product.title.like("%OmniBook%"),
                        Product.title.like("%omnibook%"),
                    )
                )
            )
        ).scalars().all()
        print("OmniBook en BD local:", len(rows))
        for r in rows:
            precio = "PEND" if r.price == 0 else str(r.price)
            print(
                f"  activo={r.is_active} | precio={precio} | costo={r.cost_price} "
                f"| hp={r.hp_price} | img={str(r.image_url)[:50]}"
            )


if __name__ == "__main__":
    asyncio.run(main())
