import pytest
from app.services.product_service import product_service
from app.schemas.product import ProductCreate


@pytest.mark.asyncio
async def test_create_product(db):
    data = ProductCreate(
        title="Test Product",
        description="A test product",
        price=29.99,
        product_type="ebook",
    )
    product = await product_service.create_product(db, data)
    assert product.title == "Test Product"
    assert float(product.price) == 29.99


@pytest.mark.asyncio
async def test_get_products(db):
    products = await product_service.get_products(db)
    assert isinstance(products, list)


@pytest.mark.asyncio
async def test_get_product_not_found(db):
    import uuid
    product = await product_service.get_product(db, uuid.uuid4())
    assert product is None
