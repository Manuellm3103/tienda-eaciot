import pytest
from sqlalchemy import select
from types import SimpleNamespace
from unittest.mock import patch

from app.models.user import User
from app.routers.admin_dashboard import _dashboard_events
from app.services.auth_service import create_access_token


async def _auth_admin(client, db) -> None:
    result = await db.execute(select(User).where(User.email == "admindash@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admindash@test.com", name="Admin", is_admin=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_dashboard_requires_admin(client, db):
    resp = await client.get("/admin/dashboard")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_dashboard_page_renders_live_partial(client, db):
    await _auth_admin(client, db)
    resp = await client.get("/admin/dashboard")
    assert resp.status_code == 200
    assert 'id="live-partial"' in resp.text
    assert "Ventas Totales" in resp.text
    assert "Estado del Contenido SEO" in resp.text


@pytest.mark.asyncio
async def test_dashboard_partial_endpoint(client, db):
    await _auth_admin(client, db)
    resp = await client.get("/admin/dashboard/partial")
    assert resp.status_code == 200
    assert "Ventas Totales" in resp.text
    assert "Pedidos Recientes" in resp.text


@pytest.mark.asyncio
async def test_ai_suggestions_partial_error_state(client, db):
    """Si la IA falla (sin key / timeout), el partial muestra error y un botón
    de reintento — nunca se queda en 'Cargando...'."""
    await _auth_admin(client, db)
    with patch(
        "app.routers.admin_dashboard.dashboard_service.get_ai_suggestions",
        new=__import__("unittest.mock").mock.AsyncMock(side_effect=RuntimeError("no IA")),
    ):
        resp = await client.get("/admin/ai/suggestions/partial")
    assert resp.status_code == 200
    assert "No se pudieron cargar" in resp.text
    assert "Cargando sugerencias" not in resp.text


@pytest.mark.asyncio
async def test_dashboard_live_sse_generator_emits_metrics(db):
    """El generador SSE (usado por /admin/dashboard/live) emite un primer
    evento 'metrics' con el HTML del partial en vivo.

    Se prueba a nivel de generador porque httpx.ASGITransport no entrega
    streams de larga duración; el formateo real de text/event-stream lo
    garantiza StreamingResponse en uvicorn."""
    fake_request = SimpleNamespace()
    gen = _dashboard_events(fake_request, db)
    try:
        first = await anext(gen)
        assert first.startswith("event: metrics")
        assert '"html"' in first
        assert "Ventas Totales" in first
    finally:
        await gen.aclose()
