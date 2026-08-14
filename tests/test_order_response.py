import pytest
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.product import Product, Category
from app.models.user import User
from app.models.order import Order, OrderItem
from app.schemas.order import OrderResponse


async def _order_with_items(db):
    category = Category(name="Resp Cat", slug="resp-cat")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    product = Product(
        title="Resp Product", description="d", price=50, stock=5,
        category_id=category.id, product_type="fisico",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    user = User(email="resp.buyer@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    order = Order(user_id=user.id, subtotal=50, total_amount=50)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=1, price_at_purchase=50))
    await db.commit()
    return order


@pytest.mark.asyncio
async def test_order_serializes_with_items(db):
    """Regression: OrderResponse requires `items`, so Order needs an `items`
    relationship (it was missing, breaking GET/POST /orders/)."""
    order = await _order_with_items(db)

    # Force a fresh load (the identity map would otherwise return the cached
    # instance, bypassing the selectin eager-load of `items`).
    db.expunge_all()
    loaded = (
        await db.execute(
            select(Order)
            .where(Order.id == order.id)
            .options(selectinload(Order.items))
        )
    ).scalar_one()

    response = OrderResponse.model_validate(loaded)
    assert len(response.items) == 1
    assert response.items[0].product_id is not None
    assert response.total_amount == Decimal("50")
