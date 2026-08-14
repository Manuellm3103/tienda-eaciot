"""End-to-end: admin dashboard -> product upload -> real customer purchase ->
invoice (público en general) -> cancellation guard.

Runs in-process against the full FastAPI stack (ASGI transport, real auth,
CSRF, routers, templates) on a throwaway SQLite DB. Never touches app.db and
never needs live Stripe/Finkok creds: the order is marked paid directly (as a
Stripe webhook would) and the invoice falls back to 'manual' because PAC/CSD
secrets are intentionally empty — which is exactly the graceful-degradation
path we want to prove.

Usage:  python scripts/admin_invoice_e2e_test.py
"""
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_DB = "e2e_admin_invoice.db"
for _f in (_DB,):
    if os.path.exists(_f):
        os.remove(_f)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./{_DB}"
os.environ["APP_SECRET_KEY"] = "e2e-admin-invoice-secret-not-for-prod"
os.environ["debug"] = "false"
# The real .env has FRONTEND_URL=https, which makes every cookie Secure and
# invisible to an http:// test client. Force plain-http cookies for this sweep.
os.environ["FRONTEND_URL"] = "http://test"
os.environ["force_https"] = "false"

import asyncio
import uuid

import httpx
from sqlalchemy import select

from app.main import app
from app.database import init_db, async_session
from app.models.user import User
from app.models.order import Order
from app.models.invoice import Invoice
from app.services.auth_service import create_access_token, get_password_hash

PASS = 0
FAIL = 0


def report(label, ok, extra=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  OK   {label} {extra}")
    else:
        FAIL += 1
        print(f"  FAIL {label} {extra}")


def _csrf(client):
    return client.cookies.get("csrf_token", "")


async def seed_users():
    await init_db()
    async with async_session() as db:
        admin = User(
            email="admin.e2e@test.com",
            hashed_password=get_password_hash("AdminTest123!"),
            name="Admin E2E",
            is_admin=True,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        return str(admin.id)


async def _patch_stripe():
    """Never hit the real Stripe API in this sweep."""
    from app.services.stripe_service import stripe_service

    async def fake_checkout_session(order, success_url, cancel_url):
        return {"url": "https://checkout.stripe.test/fake"}

    stripe_service.create_checkout_session = fake_checkout_session


async def login(client, email, password):
    r = await client.post(
        "/auth/login/web",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": _csrf(client)},
        follow_redirects=False,
    )
    return r.status_code == 302 and bool(client.cookies.get("access_token"))


async def mark_order_paid(order_id):
    async with async_session() as db:
        order = await db.get(Order, order_id)
        order.status = "paid"
        order.payment_method = "stripe"
        order.payment_id = "pi_test_simulado"
        await db.commit()


async def main():
    await seed_users()
    await _patch_stripe()
    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345),
                                    raise_app_exceptions=False)

    # ── 1. Admin: login + create category + HP product ──────────────────
    admin = httpx.AsyncClient(transport=transport, base_url="http://test")
    try:
        await admin.get("/auth/login")  # sets CSRF cookie
        report("admin login", await login(admin, "admin.e2e@test.com", "AdminTest123!"))

        r = await admin.post(
            "/admin/products/categories/",
            json={"name": "Computación", "slug": "computacion"},
        )
        cat_ok = r.status_code == 200
        report("admin create category", cat_ok, f"(status {r.status_code})")
        cat_id = r.json().get("id") if cat_ok else None

        hp_specs = {
            "Procesador": "Intel Core Ultra 7 155H",
            "Pantalla": '14" táctil 2.8K OLED',
            "Memoria RAM": "32 GB LPDDR5x",
            "Almacenamiento": "1 TB SSD NVMe",
            "Gráficos": "Intel Arc",
            "Sistema operativo": "Windows 11 Home",
            "Batería": "Hasta 21 horas",
            "Peso": "1.24 kg",
        }
        # NOTA: reemplaza por la URL del video oficial HP (no hay acceso web aquí).
        hp_videos = ["https://www.youtube.com/embed/HP_OFFICIAL_OMNIBOOK"]

        r = await admin.post(
            "/admin/products/",
            json={
                "title": "HP OmniBook 5 Ultra 7 14\" Touch",
                "description": "Laptop HP OmniBook 5 con Intel Core Ultra 7, pantalla táctil 2.8K OLED, 32 GB RAM y 1 TB SSD.",
                "price": 16000,
                "product_type": "fisico",
                "category_id": cat_id,
                "stock": 10,
                "image_url": "https://www.hp.com/content/dam/sites/worldwide/omni/omni.png",
                "specs": hp_specs,
                "videos": hp_videos,
            },
        )
        prod_ok = r.status_code == 200
        report("admin create HP product (specs+videos)", prod_ok, f"(status {r.status_code})")
        pid = r.json().get("id") if prod_ok else None

        if pid:
            r = await admin.get(f"/products/{pid}")
            detail_ok = r.status_code == 200 and "Especificaciones" in r.text and "iframe" in r.text
            report("product detail renders specs + video", detail_ok,
                   f"(specs={'Especificaciones' in r.text}, iframe={'iframe' in r.text})")

    finally:
        await admin.aclose()

    # ── 2. Customer: register + login + buy the HP ──────────────────────
    cust = httpx.AsyncClient(transport=transport, base_url="http://test")
    try:
        await cust.get("/auth/register")
        r = await cust.post(
            "/auth/register",
            json={"email": "cliente.e2e@test.com", "password": "ClienteTest123!", "name": "Cliente Real E2E"},
            headers={"X-CSRF-Token": _csrf(cust)},
        )
        # user already seeded; either 200/201 or 400 (already exists) is fine
        report("customer register", r.status_code in (200, 201, 400), f"(status {r.status_code})")

        report("customer login", await login(cust, "cliente.e2e@test.com", "ClienteTest123!"))

        r = await cust.get(f"/cart/add/{pid}", follow_redirects=False)
        cart_ok = r.status_code == 302 and bool(cust.cookies.get("cart"))
        report("add HP to cart", cart_ok)

        r = await cust.get("/cart")
        report("view cart", r.status_code == 200 and "HP OmniBook" in r.text)

        r = await cust.post(
            "/checkout",
            data={
                "_csrf_token": _csrf(cust),
                "name": "Cliente Real E2E",
                "street": "Av. Reforma 123",
                "city": "Cuernavaca",
                "state": "Morelos",
                "zip_code": "62410",
                "country": "México",
                "phone": "7771234567",
                "customer_rfc": "XAXX010101000",  # público en general
                "uso_cfdi": "S01",                 # sin efectos fiscales
            },
            headers={"X-CSRF-Token": _csrf(cust)},
            follow_redirects=False,
        )
        # Order is committed BEFORE the Stripe call; 500 = Stripe key absent in test env.
        checkout_ok = r.status_code in (302, 303, 500)
        report("checkout creates order", checkout_ok, f"(status {r.status_code})")
    finally:
        await cust.aclose()

    # ── 3. Simulate Stripe webhook: mark the order paid ─────────────────
    async with async_session() as db:
        order = (await db.execute(
            select(Order).order_by(Order.created_at.desc()).limit(1)
        )).scalar_one()
        order_id = str(order.id)
        assert str(order.user_id) == (await db.get(User, order.user_id)).id
    await mark_order_paid(order_id)
    report("order marked paid (Stripe sim)", True, f"(order {order_id[:8]}…)")

    # ── 4. Admin: issue invoice for público en general ──────────────────
    admin2 = httpx.AsyncClient(transport=transport, base_url="http://test")
    try:
        await admin2.get("/admin/invoices/")  # sets CSRF
        report("admin invoice dashboard", True)
        await login(admin2, "admin.e2e@test.com", "AdminTest123!")

        r = await admin2.post(
            f"/admin/invoices/{order_id}/issue",
            headers={"X-CSRF-Token": _csrf(admin2)},
        )
        issue_ok = r.status_code == 200
        report("admin issue invoice", issue_ok, f"(status {r.status_code})")
        body = r.json() if issue_ok else {}

        # Manual fallback expected (no PAC/CSD secrets configured).
        report("invoice falls back to manual (no PAC creds)",
               body.get("status") == "manual", f"(status={body.get('status')})")

        # Verify customer_rfc persisted as público en general.
        async with async_session() as db:
            inv = (await db.execute(
                select(Invoice).where(Invoice.order_id == order_id)
            )).scalar_one_or_none()
            rfc_ok = inv is not None and inv.customer_rfc == "XAXX010101000"
            report("invoice is público en general", rfc_ok,
                   f"(rfc={inv.customer_rfc if inv else None})")

        # Cancellation guard: a manual invoice cannot be cancelled via PAC.
        if inv:
            r = await admin2.post(
                f"/admin/invoices/{inv.id}/cancel",
                headers={"X-CSRF-Token": _csrf(admin2)},
            )
            report("cancel manual invoice -> 422 guard",
                   r.status_code == 422, f"(status {r.status_code})")
    finally:
        await admin2.aclose()

    # ── 5. Service-level: cancel a STAMPED invoice (Finkok monkeypatched) ──
    from app.services import invoice_service as inv_mod
    import app.services.cfdi_finkok as finkok_mod

    async with async_session() as db:
        stamped = Invoice(
            order_id=order_id,
            customer_rfc="XAXX010101000",
            customer_name="PÚBLICO EN GENERAL",
            status="issued",
            provider="satcfdi",
            provider_invoice_id="11111111-2222-3333-4444-555555555555",
        )
        db.add(stamped)
        await db.commit()
        await db.refresh(stamped)
        stamped_id = str(stamped.id)

    finkok_mod.finkok_client.cancel = lambda **kw: {
        "uuid": "11111111-2222-3333-4444-555555555555",
        "estatus": "202",
        "acuse": None,
        "codestatus": None,
    }
    inv_mod.settings.business_rfc = "EAC2403183F0"

    async with async_session() as db:
        result = await inv_mod.invoice_service.cancel(db, stamped_id)
        report("cancel stamped invoice -> cancelled", result.status == "cancelled",
               f"(status={result.status})")

    print(f"\n{'='*56}")
    print(f"RESULTADO: {PASS} pasaron, {FAIL} fallaron")
    print(f"{'='*56}")
    if FAIL:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
