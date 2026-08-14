import pytest
from sqlalchemy import select
from app.models.product import Product, Category
from app.models.user import User
from app.models.order import Order, OrderItem
from app.services.order_service import order_service


async def _product(db, stock, title="Inv Product", slug="inv"):
    category = Category(name=title, slug=slug)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    p = Product(
        title=title,
        description="demo",
        price=10,
        stock=stock,
        category_id=category.id,
        product_type="fisico",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _order(db, user_id, product, qty=2):
    order = Order(user_id=user_id, subtotal=10, total_amount=10)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=qty, price_at_purchase=10))
    await db.commit()
    return order


@pytest.mark.asyncio
async def test_decrement_stock_finite(db):
    product = await _product(db, stock=10)
    user = User(email="inv1@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    order = await _order(db, user.id, product, qty=3)
    decremented = await order_service.decrement_stock(db, order.id)
    await db.commit()

    await db.refresh(product)
    assert decremented == 1
    assert product.stock == 7


@pytest.mark.asyncio
async def test_unlimited_stock_untouched(db):
    product = await _product(db, stock=-1, title="Unlimited", slug="unlimited")
    user = User(email="inv2@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    order = await _order(db, user.id, product, qty=5)
    decremented = await order_service.decrement_stock(db, order.id)
    await db.commit()

    await db.refresh(product)
    assert decremented == 0
    assert product.stock == -1
