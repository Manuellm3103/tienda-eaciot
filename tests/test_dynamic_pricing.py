import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.product import Category, Product
from app.models.user_event import UserEvent
from app.services.auth_service import create_access_token
from app.services.dynamic_pricing import dynamic_pricing
from app.services.product_service import product_service
from app.schemas.product import ProductCreate


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
async def test_dynamic_pricing_recommendations(client, db):
    await _auth_admin(client, db)

    category = Category(name="Pricing", slug="pricing")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto en liquidación",
            description="Desc",
            price=100,
            category_id=category.id,
            product_type="fisico",
            stock=100,
        ),
    )
    await db.commit()

    recs = await dynamic_pricing.get_recommendations(db, limit=50)
    found = next((r for r in recs if r["product_id"] == str(product.id)), None)
    assert found is not None
    assert found["signal"] == "clearance"
    assert found["suggested_price"] < found["current_price"]


@pytest.mark.asyncio
async def test_dynamic_pricing_apply_price(client, db):
    await _auth_admin(client, db)

    category = Category(name="Apply", slug="apply")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto a precio",
            description="Desc",
            price=200,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        ),
    )
    await db.commit()

    await client.get("/admin/pricing/")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    response = await client.post(
        "/admin/pricing/apply",
        json={"product_id": str(product.id), "new_price": 175.50, "_csrf_token": csrf},
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_price"] == 175.50

    await db.refresh(product)
    assert float(product.price) == 175.50
    assert product.base_price is not None


@pytest.mark.asyncio
async def test_dynamic_pricing_toggle_auto(client, db):
    await _auth_admin(client, db)

    category = Category(name="Toggle", slug="toggle")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto auto",
            description="Desc",
            price=300,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        ),
    )
    await db.commit()

    await client.get("/admin/pricing/")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    response = await client.post(
        "/admin/pricing/toggle",
        json={"product_id": str(product.id), "enabled": True, "_csrf_token": csrf},
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 200
    assert response.json()["dynamic_pricing_enabled"] is True


@pytest.mark.asyncio
async def test_dynamic_pricing_refresh_analytics(client, db):
    await _auth_admin(client, db)

    category = Category(name="Refresh", slug="refresh")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto eventos",
            description="Desc",
            price=100,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        ),
    )
    await db.commit()

    db.add(UserEvent(user_id=None, product_id=str(product.id), event_type="view"))
    db.add(UserEvent(user_id=None, product_id=str(product.id), event_type="cart_add"))
    await db.commit()

    count = await dynamic_pricing.refresh_product_analytics(db)
    assert count >= 1
