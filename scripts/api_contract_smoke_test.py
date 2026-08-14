"""API contract smoke test.

Iterates every OpenAPI operation and asserts three contracts:

1. **Fail-closed** — an unauthenticated request to any `/admin/*` route MUST be
   rejected (401/403). A 200 here is a privilege-escalation bug.
2. **No 500s** — no operation may return an Internal Server Error.
3. **Admin reachability** — every admin GET route accepts an admin session
   (status not 401/403), proving the wiring is live, not a stub.

Runs against a throwaway SQLite DB (`smoke_test.db`) — it never touches
`app.db`. Network / side-effect operations (Stripe, LLM chat, RFC PAC) are
skipped.

Usage:  python scripts/api_contract_smoke_test.py
Exit:   0 if all contracts hold, 1 otherwise.
"""

import os
import sys

# Anchor `app` to THIS project's package. Running `python scripts/foo.py` puts
# `scripts/` on sys.path but NOT the project root, and an unrelated
# `C:\Users\Manu\azurdesk-ai-py` is installed editable on site-packages — so a
# bare `import app` would resolve to the WRONG project. Pin the root first.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./smoke_test.db"
os.environ["APP_SECRET_KEY"] = "smoke-test-secret-not-for-prod"
os.environ["debug"] = "false"

# Fresh throwaway DB every run (previous runs leave rows behind).
for _db in ("smoke_test.db",):
    if os.path.exists(_db):
        os.remove(_db)

import asyncio
from collections import defaultdict

import httpx

from app.main import app
from app.database import init_db, async_session
from app.models.user import User
from app.models.product import Category, Product
from app.services.auth_service import create_access_token

# Neutralize the in-memory rate limiter (60/min per IP) — this is a local
# contract sweep, not an abuse test.
from app.middleware.rate_limit import rate_limiter
rate_limiter.requests_per_minute = 100_000

# Operations that would hit an external service / cause side effects.
SKIP_OPERATIONS = {
    ("post", "/payments/stripe/create"),
    ("post", "/payments/stripe/webhook"),
    ("get", "/api/chat/"),
    ("post", "/api/chat/"),
    ("post", "/invoices/validate-rfc"),
}

ADMIN_PREFIX = "/admin"

# Sensible query params for GET routes that require them.
QUERY_PARAMS = {
    "/search/": {"q": "smoke"},
    "/search/suggest": {"q": "smoke"},
    "/search/expanded": {"q": "smoke"},
}


def _fill_path_params(path: str, prod_id: str, cat_id: str) -> str:
    """Replace {param} placeholders with synthetic (or seeded) values."""
    for name in ["order_id", "review_id", "refund_id", "shipment_id",
                 "address_id", "user_id", "id", "payment_id", "invoice_id"]:
        path = path.replace("{" + name + "}", "nonexistent-id")
    path = path.replace("{product_id}", prod_id)
    path = path.replace("{category_id}", cat_id)
    path = path.replace("{slug}", "smoke-cat")
    return path


async def seed():
    """Create throwaway data and return admin/customer tokens + ids."""
    await init_db()
    async with async_session() as db:
        cat = Category(name="Smoke Cat", slug="smoke-cat")
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
        prod = Product(
            title="Smoke Product", description="d", price=100, stock=10,
            category_id=cat.id, product_type="fisico",
        )
        db.add(prod)
        await db.commit()
        await db.refresh(prod)
        admin = User(email="smoke.admin@test.com", is_admin=True, is_active=True)
        cust = User(email="smoke.cust@test.com", is_admin=False, is_active=True)
        db.add_all([admin, cust])
        await db.commit()
        await db.refresh(admin)
        await db.refresh(cust)
        return (
            create_access_token({"sub": str(admin.id)}),
            create_access_token({"sub": str(cust.id)}),
            str(prod.id),
            str(cat.id),
        )


def _method(path: str, methods: dict) -> str:
    for m in ("get", "post", "put", "patch", "delete"):
        if m in methods:
            return m
    return ""


async def run():
    admin_tok, cust_tok, prod_id, cat_id = await seed()
    spec = app.openapi()
    paths = spec["paths"]

    transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 12345),
                                    raise_app_exceptions=False)
    results = defaultdict(list)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as anon, \
               httpx.AsyncClient(transport=transport, base_url="http://test",
                                 cookies={"access_token": admin_tok}) as admin:
        for path, methods in sorted(paths.items()):
            for method in ("get", "post", "put", "patch", "delete"):
                if method not in methods:
                    continue
                key = (method, path)
                if key in SKIP_OPERATIONS:
                    continue
                is_admin = path.startswith(ADMIN_PREFIX)
                url = _fill_path_params(path, prod_id, cat_id)
                params = QUERY_PARAMS.get(path)

                # 1) Unauthenticated — every route, contract: not 500; admin: fail-closed.
                r = await anon.request(method, url, params=params)
                unauth_status = r.status_code
                if unauth_status == 500:
                    results["500_unauth"].append(f"{method.upper()} {path}")
                if is_admin and unauth_status not in (401, 403):
                    results["admin_leak"].append(
                        f"{method.upper()} {path} -> {unauth_status}"
                    )

                # 2) Admin-authenticated — read-only GET routes must be reachable.
                if is_admin and method == "get":
                    r = await admin.request(method, url, params=params)
                    st = r.status_code
                    if st == 500:
                        results["500_admin_get"].append(f"GET {path}")
                    elif st in (401, 403):
                        results["admin_get_rejected"].append(f"GET {path} -> {st}")
                    else:
                        results["admin_get_ok"].append(f"GET {path} -> {st}")

    # 3) Customer-authenticated sanity — account routes must resolve as a client.
    async with httpx.AsyncClient(transport=transport, base_url="http://test",
                                 cookies={"access_token": cust_tok}) as c:
        for path in ("/orders/", "/wishlist/", "/loyalty/"):
            r = await c.get(path)
            st = r.status_code
            if st == 500:
                results["500_customer_get"].append(f"GET {path}")
            elif st == 401:
                results["customer_get_rejected"].append(f"GET {path} -> {st}")
            else:
                results["customer_get_ok"].append(f"GET {path} -> {st}")

    return results


def main() -> int:
    results = asyncio.run(run())
    total_ops = len(app.openapi()["paths"])
    print("=== API CONTRACT SMOKE TEST ===")
    print(f"OpenAPI operations: {total_ops}")
    print(f"Admin GET routes reachable as admin: {len(results['admin_get_ok'])}")
    print(f"Customer account routes resolved: {len(results['customer_get_ok'])}")
    print(f"Admin GET routes wrongly rejected: {len(results['admin_get_rejected'])}")
    print(f"Customer routes wrongly rejected:  {len(results['customer_get_rejected'])}")
    for v in results["admin_get_rejected"] + results["customer_get_rejected"]:
        print("   REJECTED:", v)

    problems = 0
    if results["500_unauth"]:
        problems += 1
        print(f"\n[FAIL] 500 on unauthenticated request ({len(results['500_unauth'])}):")
        for v in results["500_unauth"]:
            print("   ", v)
    if results["500_admin_get"]:
        problems += 1
        print(f"\n[FAIL] 500 on admin GET ({len(results['500_admin_get'])}):")
        for v in results["500_admin_get"]:
            print("   ", v)
    if results["500_customer_get"]:
        problems += 1
        print(f"\n[FAIL] 500 on customer GET ({len(results['500_customer_get'])}):")
        for v in results["500_customer_get"]:
            print("   ", v)
    if results["admin_leak"]:
        problems += 1
        print(f"\n[CRITICAL] Admin route NOT fail-closed ({len(results['admin_leak'])}):")
        for v in results["admin_leak"]:
            print("   ", v)
    if results["admin_get_rejected"]:
        problems += 1
        print(f"\n[FAIL] Admin session rejected on admin GET ({len(results['admin_get_rejected'])}):")
        for v in results["admin_get_rejected"]:
            print("   ", v)

    if not problems:
        print("\nALL CONTRACTS HOLD [OK]")
        return 0
    print("\nCONTRACT VIOLATIONS DETECTED [FAIL]")
    return 1


if __name__ == "__main__":
    sys.exit(main())
