import io
import pytest
from PIL import Image
from sqlalchemy import select
from app.models.user import User
from app.models.product import Category
from app.services.auth_service import create_access_token
from app.services.image_enhance_service import image_enhance_service
from app.services.product_service import product_service
from app.schemas.product import ProductCreate


def _make_image() -> bytes:
    img = Image.new("RGB", (400, 300), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _auth_admin(client, db) -> None:
    result = await db.execute(select(User).where(User.email == "admin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admin@test.com", name="Admin", is_admin=True)
        db.add(user)
    else:
        user.is_admin = True
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)


def test_enhance_product_photo_returns_png(monkeypatch):
    def fake_remove(img):
        return img.convert("RGBA")

    monkeypatch.setattr(
        "app.services.image_enhance_service.ImageEnhancementService._ensure_rembg",
        lambda self: fake_remove,
    )

    enhanced = image_enhance_service.enhance_product_photo(_make_image())
    result = Image.open(io.BytesIO(enhanced))
    assert result.format == "PNG"
    assert result.size == (800, 800)


def test_generate_social_media_square_returns_png():
    square = image_enhance_service.generate_social_media_square(
        _make_image(), text="Oferta"
    )
    result = Image.open(io.BytesIO(square))
    assert result.format == "PNG"
    assert result.size == (1080, 1080)


@pytest.mark.asyncio
async def test_admin_enhance_photo_endpoint(client, db, monkeypatch):
    await _auth_admin(client, db)

    category = Category(name="Fotos", slug="fotos")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto con imagen",
            description="Desc",
            price=100,
            category_id=category.id,
            product_type="fisico",
            stock=5,
            image_url="https://example.com/image.png",
        ),
    )
    await db.commit()

    def fake_remove(img):
        return img.convert("RGBA")

    monkeypatch.setattr(
        "app.services.image_enhance_service.ImageEnhancementService._ensure_rembg",
        lambda self: fake_remove,
    )

    async def fake_fetch(_url):
        return _make_image()

    monkeypatch.setattr("app.routers.admin_photos._fetch_image", fake_fetch)

    await client.get("/admin/products/")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    response = await client.post(
        f"/admin/products/{product.id}/enhance-photo",
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_admin_enhance_photo_requires_image(client, db):
    await _auth_admin(client, db)

    category = Category(name="NoImg", slug="no-img")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Sin imagen",
            description="Desc",
            price=100,
            category_id=category.id,
            product_type="fisico",
            stock=5,
        ),
    )
    await db.commit()

    await client.get("/admin/products/")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    response = await client.post(
        f"/admin/products/{product.id}/enhance-photo",
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_social_square_endpoint(client, db, monkeypatch):
    await _auth_admin(client, db)

    category = Category(name="Social", slug="social")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto social",
            description="Desc",
            price=100,
            category_id=category.id,
            product_type="fisico",
            stock=5,
            image_url="https://example.com/image.png",
        ),
    )
    await db.commit()

    async def fake_fetch(_url):
        return _make_image()

    monkeypatch.setattr("app.routers.admin_photos._fetch_image", fake_fetch)

    await client.get("/admin/products/")
    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    response = await client.post(
        f"/admin/products/{product.id}/social-square",
        headers={"X-CSRF-Token": csrf or ""},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
