import pytest
from io import BytesIO
from sqlalchemy import select
from app.models.user import User
from app.models.saved_report import SavedReport
from app.services.auth_service import create_access_token
from app.services.ai_analytics import ai_analytics
from app.services.chart_service import chart_service


async def _auth_admin(client, db) -> None:
    result = await db.execute(select(User).where(User.email == "admin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admin@test.com", name="Admin", is_admin=True)
        db.add(user)
    else:
        user.is_admin = True
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_ai_analytics_ask_returns_data(client, db, monkeypatch):
    await _auth_admin(client, db)

    async def fake_answer(_db, _question):
        return {
            "question": _question,
            "sql": "SELECT 1",
            "chart_type": "bar",
            "explanation": "Test",
            "columns": ["x", "y"],
            "data": [["a", 10], ["b", 20]],
            "row_count": 2,
        }

    monkeypatch.setattr(ai_analytics, "answer_question", fake_answer)

    await client.get("/admin/analytics/")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    response = await client.post(
        "/admin/analytics/ask",
        json={"question": "ventas totales"},
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["columns"] == ["x", "y"]
    assert data["row_count"] == 2


@pytest.mark.asyncio
async def test_ai_analytics_save_report(client, db):
    await _auth_admin(client, db)

    await client.get("/admin/analytics/")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    response = await client.post(
        "/admin/analytics/reports",
        json={
            "name": "Ventas mensuales",
            "question": "ventas por mes",
            "sql": "SELECT month, total FROM sales",
            "chart_type": "line",
        },
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Ventas mensuales"
    assert data["chart_type"] == "line"


@pytest.mark.asyncio
async def test_chart_service_render_bar():
    pytest.importorskip("matplotlib")
    image = chart_service.render("bar", ["Categoría", "Ventas"], [["A", 10], ["B", 20]])
    assert isinstance(image, bytes)
    assert len(image) > 0


def test_chart_service_render_number():
    pytest.importorskip("matplotlib")
    image = chart_service.render("number", ["Total"], [[1500.50]])
    assert isinstance(image, bytes)
    assert len(image) > 0


def test_chart_service_unavailable_without_matplotlib():
    import sys
    real_matplotlib = sys.modules.get("matplotlib")
    if real_matplotlib:
        del sys.modules["matplotlib"]
    try:
        with pytest.raises(RuntimeError, match="matplotlib is not installed"):
            chart_service.render("bar", ["x", "y"], [["a", 1]])
    finally:
        if real_matplotlib:
            sys.modules["matplotlib"] = real_matplotlib
