"""Admin routes must never render for anonymous users.

Regression: in FastAPI 0.110 a plain dependency returning a Response is
silently discarded and the handler still runs (leaking the page). The
protection must go through LoginRequired -> exception handler -> 303.
"""
import pytest

from app.models.user import User
from app.services.auth_service import create_access_token, get_password_hash


async def _create_admin(db, email="admin@test.com", password="Admin123!"):
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        name="Admin",
        is_admin=True,
        email_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
async def test_admin_dashboard_redirects_anonymous_browser(client, db):
    r = await client.get("/admin/dashboard", headers={"Accept": "text/html"})
    assert r.status_code == 303
    assert "/auth/login?next=" in r.headers["location"]


@pytest.mark.asyncio
async def test_admin_dashboard_401_for_api_client(client, db):
    r = await client.get("/admin/dashboard", headers={"Accept": "application/json"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_pages_redirect_all_anonymous(client, db):
    for path in ("/admin/invoices/", "/admin/loyalty/", "/admin/fraud/", "/admin/marketing/"):
        r = await client.get(path, headers={"Accept": "text/html"})
        assert r.status_code == 303, path
        assert "/auth/login?next=" in r.headers["location"], path


@pytest.mark.asyncio
async def test_admin_dashboard_accessible_for_admin(client, db):
    admin = await _create_admin(db)
    await db.commit()
    token = create_access_token(data={"sub": str(admin.id)})
    r = await client.get(
        "/admin/dashboard",
        headers={"Accept": "text/html", "Cookie": f"access_token={token}"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_forbidden_for_regular_user(client, db):
    user = User(email="user@test.com", hashed_password=get_password_hash("Pass123!"), name="User")
    db.add(user)
    await db.commit()
    token = create_access_token(data={"sub": str(user.id)})
    r = await client.get(
        "/admin/dashboard",
        headers={"Accept": "application/json", "Cookie": f"access_token={token}"},
    )
    assert r.status_code == 403
