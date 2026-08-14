import pytest
from decimal import Decimal
from sqlalchemy import select
from app.models.product import Product, Category
from app.models.user import User
from app.models.product_variant import ProductVariant
from app.models.order import Order, OrderItem
from app.services.auth_service import create_access_token
from app.services.variant_service import variant_service
from app.services.order_service import order_service
from app.schemas.order import OrderCreate, OrderItemCreate


async def _product(db, title="Variant Product", slug="vcat"):
    category = Category(name=title, slug=slug)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    p = Product(
        title=title, description="demo", price=50, stock=10,
        category_id=category.id, product_type="fisico",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


@pytest.mark.asyncio
async def test_variant_crud(db):
    product = await _product(db, slug="vcat-crud")
    v = await variant_service.create_variant(
        db, product.id, "Talla M", price_delta=Decimal("5"), stock=3
    )
    await db.commit()
    assert v.id

    variants = await variant_service.list_variants(db, product.id)
    assert len(variants) == 1
    assert variants[0].name == "Talla M"

    updated = await variant_service.update_variant(db, v.id, stock=0)
    assert updated.stock == 0

    assert await variant_service.delete_variant(db, v.id) is True


@pytest.mark.asyncio
async def test_order_with_variant_price(db):
    product = await _product(db, slug="vcat-order")
    variant = await variant_service.create_variant(
        db, product.id, "Talla L", price_delta=Decimal("10"), stock=5
    )
    await db.commit()
    user = User(email="variant.buyer@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    data = OrderCreate(
        items=[OrderItemCreate(product_id=product.id, quantity=2, variant_id=variant.id)],
        shipping_address={},
    )
    order = await order_service.create_order(db, user.id, data)
    await db.commit()

    assert float(order.subtotal) == 120.00  # (50 + 10) * 2

    item = (
        await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    ).scalar_one()
    assert str(item.variant_id) == str(variant.id)
    assert item.variant_name == "Talla L"
    assert float(item.price_at_purchase) == 60.00


@pytest.mark.asyncio
async def test_admin_variants_endpoints_require_admin(client, db):
    product = await _product(db, slug="vcat-admin")
    # unauthenticated -> 401/403
    resp = await client.get(f"/admin/products/{product.id}/variants")
    assert resp.status_code in (401, 403)
