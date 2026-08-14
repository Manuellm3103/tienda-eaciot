import pytest
from sqlalchemy import select
from app.models.support_ticket import SupportTicket
from app.models.user import User
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_support_page_renders(client):
    resp = await client.get("/soporte")
    assert resp.status_code == 200
    assert "Soporte" in resp.text


@pytest.mark.asyncio
async def test_create_ticket(client, db):
    # middleware emits csrf cookie on first response
    resp = await client.get("/soporte")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    assert csrf

    resp = await client.post(
        "/soporte",
        data={"email": "cliente@test.com", "subject": "Pedido no llega", "message": "Hola, ¿dónde está mi pedido?"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 302

    tickets = (await db.execute(select(SupportTicket))).scalars().all()
    assert any(t.subject == "Pedido no llega" for t in tickets)


@pytest.mark.asyncio
async def test_admin_support_requires_admin(client):
    resp = await client.get("/admin/support/list")
    assert resp.status_code in (401, 403)
