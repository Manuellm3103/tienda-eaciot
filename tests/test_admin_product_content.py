import pytest
from app.routers.admin_products import _parse_specs, _parse_videos, _normalize_video
from app.models.product import Category, Product
from app.services.product_service import product_service
from app.schemas.product import ProductCreate


def test_parse_specs_lines():
    text = "Procesador: Intel Core Ultra 7\nRAM: 32 GB\n\nClave sin valor\n"
    assert _parse_specs(text) == {
        "Procesador": "Intel Core Ultra 7",
        "RAM": "32 GB",
    }
    assert _parse_specs("") is None


def test_parse_videos_normalizes_youtube():
    text = (
        "https://www.youtube.com/watch?v=abc123XYZ\n"
        "https://youtu.be/def456UVW\n"
        "https://www.youtube.com/shorts/ghi789\n"
    )
    assert _parse_videos(text) == [
        "https://www.youtube.com/embed/abc123XYZ",
        "https://www.youtube.com/embed/def456UVW",
        "https://www.youtube.com/embed/ghi789",
    ]
    assert _parse_videos("") is None


def test_normalize_video_passthrough():
    assert _normalize_video("https://www.youtube.com/embed/abc123") == "https://www.youtube.com/embed/abc123"


@pytest.mark.asyncio
async def test_create_product_with_specs_and_videos(db):
    category = Category(name="Laptops", slug="laptops-e2e")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    data = ProductCreate(
        title="HP OmniBook 5 Ultra 7",
        description="Laptop táctil",
        price=16000,
        category_id=category.id,
        product_type="fisico",
        stock=10,
        specs={"Procesador": "Intel Core Ultra 7", "RAM": "32 GB"},
        videos=["https://www.youtube.com/embed/abc123"],
    )
    product = await product_service.create_product(db, data)
    await db.commit()
    await db.refresh(product)

    assert product.specs["Procesador"] == "Intel Core Ultra 7"
    assert product.videos == ["https://www.youtube.com/embed/abc123"]
