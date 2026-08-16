import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.marketing_decision import MarketingDecision
from app.models.product import Category, Product
from app.services.auth_service import create_access_token
from app.services.agents.marketing_orchestrator import marketing_orchestrator
from app.services.proactive_engine import proactive_engine


async def _auth_client(client, db, email: str = "marketing@test.com", admin: bool = True) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Marketing User", is_admin=admin)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


@pytest.mark.asyncio
async def test_marketing_orchestrator_routes_content(client, db):
    user = await _auth_client(client, db)
    category = Category(name="Marketing", slug="marketing")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto de Marketing",
        description="Desc",
        price=100,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    result = await marketing_orchestrator.run(
        db, f"genera contenido para producto {product.id}", session_id="mkt-1"
    )
    assert result.agent_name == "content"
    assert "Contenido generado" in result.answer

    decisions = (
        await db.execute(select(MarketingDecision).where(MarketingDecision.agent_id == "marketing_orchestrator"))
    ).scalars().all()
    assert len(decisions) >= 1


@pytest.mark.asyncio
async def test_marketing_orchestrator_routes_seo(client, db):
    await _auth_client(client, db, email="mkseo@test.com")
    result = await marketing_orchestrator.run(db, "sugiere keywords para seo", session_id="mkt-2")
    assert result.agent_name == "seo"
    assert "Sugerencias" in result.answer


@pytest.mark.asyncio
async def test_marketing_orchestrator_routes_campaign(client, db):
    await _auth_client(client, db, email="mkcampaign@test.com")
    result = await marketing_orchestrator.run(db, "campaña de navidad", session_id="mkt-3")
    assert result.agent_name == "campaign"
    assert "campaña" in result.answer.lower()


@pytest.mark.asyncio
async def test_marketing_orchestrator_routes_analytics(client, db):
    await _auth_client(client, db, email="mkanalytics@test.com")
    result = await marketing_orchestrator.run(db, "reporte de ventas", session_id="mkt-4")
    assert result.agent_name == "analytics"
    assert "Ventas" in result.answer


@pytest.mark.asyncio
async def test_admin_marketing_dashboard(client, db):
    await _auth_client(client, db, email="mkadmin@test.com")
    response = await client.get("/admin/marketing/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_marketing_ask_endpoint(client, db):
    await _auth_client(client, db, email="mkask@test.com")
    response = await client.post("/admin/marketing/ask", json={"message": "reporte de ventas"})
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "analytics"
    assert "Ventas" in data["answer"]


@pytest.mark.asyncio
async def test_proactive_engine_runs(client, db):
    await _auth_client(client, db, email="mkproactive@test.com")
    actions = await proactive_engine.run(db)
    assert isinstance(actions, list)
