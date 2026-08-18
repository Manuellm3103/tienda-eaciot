import pytest
from app.services.product_service import product_service
from app.schemas.product import ProductCreate, ProductUpdate


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
async def test_create_product_with_compare_at_price(db):
    """Anclaje de precios: el precio de competencia se guarda y es mayor."""
    data = ProductCreate(
        title="Laptop con anclaje",
        description="Precio de competencia tachado",
        price=12999.00,
        compare_at_price=15499.00,
        product_type="fisico",
    )
    product = await product_service.create_product(db, data)
    assert float(product.price) == 12999.00
    assert float(product.compare_at_price) == 15499.00
    assert product.compare_at_price > product.price


@pytest.mark.asyncio
async def test_update_product_clears_compare_at_price(db):
    """Dejar el campo vacío en el admin (None) borra el anclaje."""
    data = ProductCreate(
        title="Con anclaje",
        price=100.00,
        compare_at_price=120.00,
        product_type="fisico",
    )
    product = await product_service.create_product(db, data)
    assert product.compare_at_price is not None

    updated = await product_service.update_product(db, product.id, ProductUpdate(compare_at_price=None))
    assert updated is not None
    assert updated.compare_at_price is None


@pytest.mark.asyncio
async def test_get_products(db):
    products = await product_service.get_products(db)
    assert isinstance(products, list)


@pytest.mark.asyncio
async def test_get_product_not_found(db):
    import uuid
    product = await product_service.get_product(db, uuid.uuid4())
    assert product is None

