import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.user import User
from app.models.product import Category, Product
from app.models.order import Order, OrderItem
from app.services.auth_service import create_access_token
from app.services.inventory_forecast import inventory_forecaster


async def _auth_client(client, db, email: str = "inventory@test.com", admin: bool = True) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Inventory User", is_admin=admin)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


async def _make_paid_order(db, user: User, product: Product, quantity: int, days_ago: int):
    order = Order(
        user_id=user.id,
        subtotal=product.price * quantity,
        total_amount=product.price * quantity,
        status="paid",
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(order)
    await db.flush()
    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=quantity,
        price_at_purchase=product.price,
    )
    db.add(item)
    await db.commit()


@pytest.mark.asyncio
async def test_predict_stockout_with_sales_history(client, db):
    user = await _auth_client(client, db)
    category = Category(name="Inventory", slug="inventory")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto Popular",
        description="Desc",
        price=100,
        category_id=category.id,
        product_type="fisico",
        stock=20,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    # Sell 1 unit per day for the last 30 days
    for i in range(30):
        await _make_paid_order(db, user, product, 1, 30 - i)

    prediction = await inventory_forecaster.predict_stockout(db, str(product.id))
    assert prediction["days_until_stockout"] is not None
    assert prediction["days_until_stockout"] <= 30
    assert prediction["restock_recommendation"] > 0
    assert prediction["confidence"] in ("medium", "high")


@pytest.mark.asyncio
async def test_predict_stockout_unlimited_stock(client, db):
    await _auth_client(client, db)
    category = Category(name="InventoryDigital", slug="inventorydigital")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Ebook",
        description="Desc",
        price=50,
        category_id=category.id,
        product_type="ebook",
        stock=-1,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    prediction = await inventory_forecaster.predict_stockout(db, str(product.id))
    assert prediction["days_until_stockout"] is None
    assert prediction["restock_recommendation"] == 0


@pytest.mark.asyncio
async def test_predict_stockout_insufficient_history(client, db):
    await _auth_client(client, db)
    category = Category(name="InventoryNew", slug="inventorynew")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto Nuevo",
        description="Desc",
        price=200,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    prediction = await inventory_forecaster.predict_stockout(db, str(product.id))
    assert prediction["confidence"] == "low"
    assert prediction["days_until_stockout"] is None


@pytest.mark.asyncio
async def test_admin_inventory_dashboard(client, db):
    user = await _auth_client(client, db, email="inventoryadmin@test.com")
    category = Category(name="InventoryAdmin", slug="inventoryadmin")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto Stock Bajo",
        description="Desc",
        price=100,
        category_id=category.id,
        product_type="fisico",
        stock=5,
        reorder_point=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    response = await client.get("/admin/inventory/")
    assert response.status_code == 200
    assert b"Producto Stock Bajo" in response.content


@pytest.mark.asyncio
async def test_admin_inventory_forecast_api(client, db):
    user = await _auth_client(client, db, email="inventoryapi@test.com")
    category = Category(name="InventoryAPI", slug="inventoryapi")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto API",
        description="Desc",
        price=100,
        category_id=category.id,
        product_type="fisico",
        stock=20,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    for i in range(30):
        await _make_paid_order(db, user, product, 1, 30 - i)

    response = await client.get(f"/admin/inventory/forecast/{product.id}")
    assert response.status_code == 200
    data = response.json()
    assert "days_until_stockout" in data
    assert "restock_recommendation" in data
