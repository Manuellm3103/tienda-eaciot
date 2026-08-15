"""Idempotent bootstrap: seed demo products + create the admin user.

Runs from scripts/release.sh on every Render deploy. It is safe to run
repeatedly:

- Seeds the 6 demo products ONLY when the products table is empty (so it never
  overwrites real catalog data you've added through the admin portal).
- Creates the admin user ONLY when ADMIN_EMAIL + ADMIN_PASSWORD are both set
  in the environment AND no user with that email exists.

Set ADMIN_EMAIL / ADMIN_PASSWORD in the Render dashboard (Environment).
Without them the store still gets demo products, just no admin account.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.database import async_session, init_db  # noqa: E402
from app.models.product import Category, Product  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import get_password_hash  # noqa: E402

DEMO_PRODUCTS = [
    # (title, description, price, product_type, stock, category_slug, category_name)
    (
        "Ebook: Domina la IA",
        "Guía práctica para aplicar inteligencia artificial a tu negocio o proyecto.",
        "29.99", "ebook", 100, "productos-digitales", "Productos Digitales",
    ),
    (
        "Curso de Automatización",
        "Aprende a automatizar tareas repetitivas y ahorrar horas cada semana.",
        "99.00", "curso", 100, "productos-digitales", "Productos Digitales",
    ),
    (
        "Template Notion Pro",
        "Plantilla profesional de Notion para gestionar proyectos y tareas.",
        "19.99", "template", 100, "productos-digitales", "Productos Digitales",
    ),
    (
        "Software de Gestión",
        "Licencia de software para administrar inventario, ventas y clientes.",
        "199.00", "software", 100, "productos-digitales", "Productos Digitales",
    ),
    (
        "Camiseta Eaciot",
        "Camiseta de algodón premium con el logo de Tienda Eaciot.",
        "24.99", "fisico", 50, "productos-fisicos", "Productos Físicos",
    ),
    (
        "Taza Eaciot",
        "Taza de cerámica 11oz con diseño exclusivo de Tienda Eaciot.",
        "14.99", "fisico", 50, "productos-fisicos", "Productos Físicos",
    ),
]


async def seed_products_if_empty() -> int:
    async with async_session() as db:
        count = (await db.execute(select(Product.id))).first()
        if count:
            return 0
        cache = {}
        for (title, desc, price, ptype, stock, slug, cname) in DEMO_PRODUCTS:
            if slug not in cache:
                cat = (await db.execute(select(Category).where(Category.slug == slug))).scalar_one_or_none()
                if not cat:
                    cat = Category(name=cname, slug=slug)
                    db.add(cat)
                    await db.flush()
                cache[slug] = cat
            db.add(
                Product(
                    title=title,
                    description=desc,
                    price=price,
                    product_type=ptype,
                    stock=stock,
                    category_id=cache[slug].id,
                )
            )
        await db.commit()
        return len(DEMO_PRODUCTS)


async def create_admin_from_env() -> bool:
    email = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD") or ""
    if not email or not password:
        return False
    async with async_session() as db:
        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing:
            if not existing.is_admin:
                existing.is_admin = True
                existing.is_active = True
                await db.commit()
            return True
        db.add(
            User(
                email=email,
                hashed_password=get_password_hash(password),
                name="Admin",
                is_admin=True,
                is_active=True,
                email_verified=True,
            )
        )
        await db.commit()
        return True


async def main() -> None:
    await init_db()
    seeded = await seed_products_if_empty()
    print(f"Bootstrap: {seeded} productos demo sembrados")
    admin_created = await create_admin_from_env()
    print(f"Bootstrap: admin {'creado/verificado' if admin_created else 'omitido (falta ADMIN_EMAIL/ADMIN_PASSWORD)'}")


if __name__ == "__main__":
    asyncio.run(main())
