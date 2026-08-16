import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from app.models.user import User
from app.models.product import Category, Product
from app.models.order import Order
from app.models.fraud_score import FraudScore
from app.services.auth_service import create_access_token
from app.services.fraud_detector import fraud_detector


async def _auth_client(client, db, email: str = "fraud@test.com", admin: bool = False) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Test User", is_admin=admin)
        db.add(user)
    else:
        user.is_admin = admin
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


@pytest.mark.asyncio
async def test_fraud_detector_scores_low_risk_order(client, db):
    user = await _auth_client(client, db)

    category = Category(name="Fraud", slug="fraud")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto",
        description="Desc",
        price=100,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    order = Order(
        user_id=user.id,
        subtotal=100,
        total_amount=100,
        status="pending",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Make the account look mature so the order is genuinely low-risk.
    user.created_at = datetime.utcnow() - timedelta(days=2)
    await db.commit()

    result = await fraud_detector.score_order(db, order, client_ip="127.0.0.1")
    assert result["risk_level"] == "low"
    assert result["auto_decision"] == "approved"

    score = (
        await db.execute(select(FraudScore).where(FraudScore.order_id == str(order.id)))
    ).scalars().first()
    assert score is not None


@pytest.mark.asyncio
async def test_fraud_detector_flags_high_value_order(client, db):
    user = await _auth_client(client, db, email="fraud2@test.com")
    # Simulate a brand-new account by not changing created_at.

    order = Order(
        user_id=user.id,
        subtotal=10000,
        total_amount=10000,
        status="pending",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    result = await fraud_detector.score_order(db, order, client_ip="127.0.0.1")
    assert result["risk_level"] in ("medium", "high")
    assert result["auto_decision"] in ("flagged", "blocked")
    assert any("Monto alto" in flag for flag in result["flags"])


@pytest.mark.asyncio
async def test_create_order_triggers_fraud_score(client, db):
    user = await _auth_client(client, db, email="fraud3@test.com")

    category = Category(name="FraudAPI", slug="fraudapi")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="API Product",
        description="Desc",
        price=50,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    response = await client.post(
        "/orders/",
        json={
            "items": [{"product_id": str(product.id), "quantity": 1}],
            "shipping_address": {
                "street": "Calle 1",
                "city": "Cuernavaca",
                "state": "Morelos",
                "zip_code": "62000",
                "country": "MX",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    order_id = data["id"]

    score = (
        await db.execute(select(FraudScore).where(FraudScore.order_id == order_id))
    ).scalars().first()
    assert score is not None
    assert score.risk_level in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_fraud_admin_dashboard_requires_admin(client, db):
    response = await client.get("/admin/fraud/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_fraud_admin_dashboard_lists_scores(client, db):
    user = await _auth_client(client, db, email="fraudadmin@test.com", admin=True)
    order = Order(user_id=user.id, subtotal=100, total_amount=100, status="pending")
    db.add(order)
    await db.commit()
    await db.refresh(order)
    await fraud_detector.score_order(db, order)

    response = await client.get("/admin/fraud/")
    assert response.status_code == 200
    assert b"Antifraude" in response.content
