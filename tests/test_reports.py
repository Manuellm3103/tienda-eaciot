import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.order import Order
from app.services.auth_service import create_access_token


async def _auth_admin(client, db):
    result = await db.execute(select(User).where(User.email == "admin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admin@test.com", name="Admin", is_admin=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


@pytest.mark.asyncio
async def test_reports_require_admin(client):
    resp = await client.get("/admin/reports/sales.csv")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_sales_csv_exports_order(client, db):
    await _auth_admin(client, db)

    user = User(email="buyer.report@test.com", name="Buyer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    db.add(Order(
        user_id=user.id,
        subtotal=99.00,
        total_amount=99.00,
        status="paid",
        payment_method="stripe",
    ))
    await db.commit()

    resp = await client.get("/admin/reports/sales.csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    body = resp.text
    assert "order_id" in body
    assert "buyer.report@test.com" in body
    assert "paid" in body


@pytest.mark.asyncio
async def test_products_csv_exports_catalog(client, db):
    await _auth_admin(client, db)
    resp = await client.get("/admin/reports/products.csv")
    assert resp.status_code == 200
    assert "product_id" in resp.text
