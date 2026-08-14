import pytest
from app.models.product import Product, Category
from app.models.user import User
from app.models.order import Order, OrderItem
from app.services.recommendation_service import recommendation_service


async def _product(db, title, slug):
    category = Category(name=title, slug=slug)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    p = Product(
        title=title, description="demo", price=10, stock=5,
        category_id=category.id, product_type="fisico",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_also_bought_uses_order_cooccurrence(db):
    a = await _product(db, "Anchor", slug="cs-anchor")
    b = await _product(db, "Bundle Mate", slug="cs-mate")
    c = await _product(db, "Unrelated", slug="cs-unrelated")

    user = User(email="cross.sell@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Order 1: a + b together
    o1 = Order(user_id=user.id, subtotal=10, total_amount=10)
    db.add(o1)
    await db.commit()
    await db.refresh(o1)
    db.add_all([
        OrderItem(order_id=o1.id, product_id=a.id, quantity=1, price_at_purchase=10),
        OrderItem(order_id=o1.id, product_id=b.id, quantity=1, price_at_purchase=10),
    ])
    await db.commit()

    also = await recommendation_service.get_also_bought(db, a.id)
    assert b.id in [p.id for p in also]
    assert c.id not in [p.id for p in also]


@pytest.mark.asyncio
async def test_cart_cross_sell_excludes_existing(db):
    a = await _product(db, "Anchor2", slug="cs-anchor2")
    b = await _product(db, "Mate2", slug="cs-mate2")

    user = User(email="cross.sell2@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    o1 = Order(user_id=user.id, subtotal=10, total_amount=10)
    db.add(o1)
    await db.commit()
    await db.refresh(o1)
    db.add_all([
        OrderItem(order_id=o1.id, product_id=a.id, quantity=1, price_at_purchase=10),
        OrderItem(order_id=o1.id, product_id=b.id, quantity=1, price_at_purchase=10),
    ])
    await db.commit()

    cross = await recommendation_service.get_cart_cross_sell(db, [a.id])
    assert b.id in [p.id for p in cross]

    cross2 = await recommendation_service.get_cart_cross_sell(db, [a.id, b.id])
    assert cross2 == []  # already in cart
