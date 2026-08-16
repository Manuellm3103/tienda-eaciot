import pytest
from datetime import datetime
from app.routers.admin_products import _parse_specs, _parse_videos, _normalize_video
from app.models.product import Category, Product
from app.services.product_service import product_service
from app.services.product_content_service import product_content_service
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


def test_score_content_perfect():
    description = " ".join(["palabra"] * 120)
    content = {
        "seo_title": "Título corto",
        "meta_description": "Una meta descripción de menos de 155 caracteres.",
        "description": description,
        "search_terms": ["a", "b", "c", "d", "e"],
        "bullet_points": ["a", "b", "c"],
        "alt_texts": ["a", "b"],
    }
    content_score, seo_score = product_content_service._score_content(content)
    assert seo_score == 100.0
    assert content_score == 100.0


def test_score_content_empty():
    content_score, seo_score = product_content_service._score_content({})
    assert seo_score == 0.0
    assert content_score == 0.0


@pytest.mark.asyncio
async def test_apply_to_product_persists_scores_and_alt_texts(db, monkeypatch):
    category = Category(name="AltTexts", slug="alt-texts")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Auriculares Bluetooth",
            description=None,
            price=899,
            category_id=category.id,
            product_type="fisico",
            stock=20,
        ),
    )
    await db.commit()

    async def fake_generate(_product):
        return {
            "seo_title": "Auriculares Bluetooth México",
            "meta_description": "Compra auriculares bluetooth con envío gratis.",
            "description": "Una descripción muy completa y persuasiva que tiene más de ochenta palabras para que el score sea alto y cubra el requisito mínimo de longitud establecido.",
            "bullet_points": ["Sonido HD", "Batería 20h", "Ligero"],
            "search_terms": ["auriculares", "bluetooth", "inalámbricos", "méxico", "envío gratis"],
            "alt_texts": ["Auriculares negros", "Auriculares sobre mesa"],
        }

    monkeypatch.setattr(product_content_service, "generate_content", fake_generate)

    result = await product_content_service.apply_to_product(db, product)
    await db.commit()
    await db.refresh(product)

    assert result["status"] == "generated"
    assert product.meta_title == "Auriculares Bluetooth México"
    assert product.alt_texts == ["Auriculares negros", "Auriculares sobre mesa"]
    assert product.seo_score is not None
    assert product.content_score is not None
    assert product.content_generated_at is not None
    assert product.seo_score > 0
    assert product.content_score > 0


@pytest.mark.asyncio
async def test_batch_enrich_updates_scores(db, monkeypatch):
    category = Category(name="Batch", slug="batch-scores")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Mouse Inalámbrico",
            description=None,
            price=299,
            category_id=category.id,
            product_type="fisico",
            stock=15,
        ),
    )
    await db.commit()

    async def fake_generate(_product):
        return {
            "seo_title": "Mouse Inalámbrico",
            "meta_description": "Mouse ergonómico inalámbrico.",
            "description": "Descripción larga y persuasiva con muchas palabras para superar el umbral mínimo requerido por el servicio de scoring de contenido.",
            "bullet_points": ["Ergonómico", "USB-C", "Silencioso"],
            "search_terms": ["mouse", "inalámbrico", "usb-c", "ergonómico", "oficina"],
            "alt_texts": ["Mouse negro", "Mouse con receptor USB"],
        }

    monkeypatch.setattr(product_content_service, "generate_content", fake_generate)

    result = await product_content_service.batch_enrich(db, limit=5)
    await db.commit()

    assert result["enriched"] >= 1
    assert result["failed"] == 0
    await db.refresh(product)
    assert product.seo_score is not None
    assert product.content_score is not None
