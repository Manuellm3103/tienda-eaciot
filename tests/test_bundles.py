import pytest
from sqlalchemy import select

from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.product_bundle import ProductBundle
from app.services.bundle_service import bundle_service
from app.services.auth_service import create_access_token


async def _auth_client(client, db, email: str = "bundlesadmin@test.com", admin: bool = True) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Bundle Admin", is_admin=admin)
        db.add(user)
    else:
        user.is_admin = admin
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


class TestBundleService:
    @pytest.mark.asyncio
    async def test_mine_bundles_finds_pairs(self, db):
        p1 = Product(title="A", price=100, product_type="fisico")
        p2 = Product(title="B", price=100, product_type="fisico")
        db.add(p1)
        db.add(p2)
        await db.flush()

        user = User(email="buyer1@test.com", is_active=True)
        db.add(user)
        await db.flush()

        for _ in range(2):
            order = Order(user_id=user.id, subtotal=200, total_amount=200, status="paid")
            db.add(order)
            await db.flush()
            db.add(OrderItem(order_id=order.id, product_id=p1.id, price_at_purchase=100, quantity=1))
            db.add(OrderItem(order_id=order.id, product_id=p2.id, price_at_purchase=100, quantity=1))

        await db.commit()

        candidates = await bundle_service.mine_bundles(db, min_support=1)
        assert len(candidates) > 0
        pair_ids = set(candidates[0]["product_ids"])
        assert pair_ids == {p1.id, p2.id}

    @pytest.mark.asyncio
    async def test_generate_bundles_creates_records(self, db):
        p1 = Product(title="A", price=100, product_type="fisico")
        p2 = Product(title="B", price=100, product_type="fisico")
        db.add(p1)
        db.add(p2)
        await db.flush()

        user = User(email="buyer2@test.com", is_active=True)
        db.add(user)
        await db.flush()

        order = Order(user_id=user.id, subtotal=200, total_amount=200, status="paid")
        db.add(order)
        await db.flush()
        db.add(OrderItem(order_id=order.id, product_id=p1.id, price_at_purchase=100, quantity=1))
        db.add(OrderItem(order_id=order.id, product_id=p2.id, price_at_purchase=100, quantity=1))
        await db.commit()

        bundles = await bundle_service.generate_bundles(db, min_support=1, discount_percentage=10)
        assert len(bundles) > 0
        assert bundles[0].discount_value == 10

    @pytest.mark.asyncio
    async def test_calculate_bundle_price(self, db):
        p1 = Product(title="A", price=100, product_type="fisico")
        p2 = Product(title="B", price=50, product_type="fisico")
        db.add(p1)
        db.add(p2)
        await db.flush()

        bundle = ProductBundle(
            name="Test",
            product_ids=[p1.id, p2.id],
            discount_type="percentage",
            discount_value=20,
        )
        db.add(bundle)
        await db.flush()

        pricing = await bundle_service.calculate_bundle_price(db, bundle)
        assert pricing["original_price"] == 150.0
        assert pricing["discount"] == 30.0
        assert pricing["final_price"] == 120.0


@pytest.mark.asyncio
async def test_admin_bundles_page(client, db):
    await _auth_client(client, db)
    response = await client.get("/bundles/admin")
    assert response.status_code == 200
    assert "Combos Inteligentes IA" in response.text
