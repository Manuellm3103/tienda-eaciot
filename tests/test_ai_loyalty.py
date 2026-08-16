import pytest
from datetime import datetime, timedelta
from sqlalchemy import select
from uuid import uuid4

from app.models.user import User
from app.models.product import Category, Product
from app.models.order import Order, OrderItem
from app.models.loyalty_quest import LoyaltyQuest
from app.services.auth_service import create_access_token
from app.services.ai_loyalty_service import ai_loyalty_service


async def _auth_client(client, db, email: str = "ailoyalty@test.com", admin: bool = False) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="AI Loyalty User", is_admin=admin)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


async def _make_paid_order(db, user: User, product: Product, quantity: int, days_ago: int = 0):
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
async def test_churn_risk_high_for_inactive_user(client, db):
    user = await _auth_client(client, db)
    user.last_purchase_at = datetime.utcnow() - timedelta(days=70)
    user.purchase_count = 1
    user.total_spent = 200
    await db.commit()

    risk = await ai_loyalty_service.predict_churn_risk(db, user.id)
    assert risk["level"] == "high"
    assert risk["score"] > 0.5


@pytest.mark.asyncio
async def test_churn_risk_low_for_active_user(client, db):
    user = await _auth_client(client, db, email="active@test.com")
    user.last_purchase_at = datetime.utcnow() - timedelta(days=5)
    user.purchase_count = 5
    user.total_spent = 2000
    await db.commit()

    risk = await ai_loyalty_service.predict_churn_risk(db, user.id)
    assert risk["level"] == "low"


@pytest.mark.asyncio
async def test_retention_offer_for_at_risk(client, db):
    user = await _auth_client(client, db, email="atrisk@test.com")
    user.last_purchase_at = datetime.utcnow() - timedelta(days=45)
    user.purchase_count = 1
    await db.commit()

    offer = await ai_loyalty_service.suggest_retention_offer(db, user.id)
    assert offer["offer_type"] == "discount"
    assert offer["discount_percent"] >= 10
    assert "descuento" in offer["message"].lower()


@pytest.mark.asyncio
async def test_default_quests_created_on_insights(client, db):
    user = await _auth_client(client, db, email="quests@test.com")
    insights = await ai_loyalty_service.get_loyalty_insights(db, user.id)
    assert len(insights["active_quests"]) >= 1
    assert any(q["quest_type"] == "purchase_count" for q in insights["active_quests"])


@pytest.mark.asyncio
async def test_quest_progress_on_order_event(client, db):
    user = await _auth_client(client, db, email="questorder@test.com")
    category = Category(name="QuestCat", slug="questcat")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    product = Product(
        title="Quest Product",
        description="Desc",
        price=100,
        category_id=category.id,
        product_type="fisico",
        stock=10,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    await ai_loyalty_service.ensure_default_quests(db, user.id)
    await _make_paid_order(db, user, product, 1)
    await ai_loyalty_service.record_event(db, user.id, "order_placed")

    quests = await ai_loyalty_service.get_active_quests(db, user.id)
    purchase_quest = next((q for q in quests if q.quest_type == "purchase_count"), None)
    assert purchase_quest is not None
    assert purchase_quest.progress >= 1


@pytest.mark.asyncio
async def test_birthday_campaign(client, db):
    user = await _auth_client(client, db, email="birthday@test.com")
    today = datetime.utcnow()
    user.birthday = today - timedelta(days=365 * 30)  # Birthday is today
    await db.commit()

    offers = await ai_loyalty_service.generate_birthday_campaign(db)
    assert len(offers) >= 1
    assert any(o["user_id"] == user.id for o in offers)
    assert "cumpleaños" in offers[0]["message"].lower()


@pytest.mark.asyncio
async def test_admin_loyalty_dashboard(client, db):
    await _auth_client(client, db, email="adminloyalty@test.com", admin=True)
    response = await client.get("/admin/loyalty/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_at_risk_customers(client, db):
    user = await _auth_client(client, db, email="riskadmin@test.com", admin=True)
    user.last_purchase_at = datetime.utcnow() - timedelta(days=50)
    user.purchase_count = 1
    await db.commit()

    response = await client.get("/admin/loyalty/at-risk")
    assert response.status_code == 200
    data = response.json()
    assert any(item["user_id"] == user.id for item in data)
