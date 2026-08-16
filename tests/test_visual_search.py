import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
from PIL import Image
import numpy as np
from sqlalchemy import select

from app.models.user import User
from app.models.product import Category, Product
from app.models.product_embedding import ProductEmbedding
from app.services.auth_service import create_access_token
from app.services.visual_search import visual_search_service


async def _auth_client(client, db, email: str = "visual@test.com", admin: bool = True) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Visual User", is_admin=admin)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


def _make_image_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color="red")
    buf = BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_index_product_creates_embedding(client, db):
    user = await _auth_client(client, db)
    category = Category(name="Visual", slug="visual")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Zapato Rojo",
        description="Desc",
        price=500,
        category_id=category.id,
        product_type="fisico",
        stock=10,
        image_url="https://example.com/zapato.jpg",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    fake_emb = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    with patch.object(visual_search_service, "_encode_image", return_value=fake_emb):
        with patch.object(visual_search_service, "_fetch_image", return_value=_make_image_bytes()):
            visual_search_service._enabled = True
            ok = await visual_search_service.index_product(db, str(product.id))
            assert ok is True

    emb = (
        await db.execute(select(ProductEmbedding).where(ProductEmbedding.product_id == str(product.id)))
    ).scalars().first()
    assert emb is not None
    assert np.allclose(emb.embedding, fake_emb.tolist(), atol=1e-6)


@pytest.mark.asyncio
async def test_visual_search_endpoint(client, db):
    user = await _auth_client(client, db, email="visualapi@test.com")
    category = Category(name="VisualAPI", slug="visualapi")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Producto Similar",
        description="Desc",
        price=200,
        category_id=category.id,
        product_type="fisico",
        stock=10,
        image_url="https://example.com/similar.jpg",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    emb = ProductEmbedding(
        product_id=str(product.id),
        embedding=[1.0, 0.0, 0.0],
        model_version="test",
    )
    db.add(emb)
    await db.commit()

    with patch.object(visual_search_service, "_encode_image", return_value=np.array([1.0, 0.0, 0.0], dtype=np.float32)):
        visual_search_service._enabled = True
        response = await client.post(
            "/api/visual-search/",
            files={"image": ("query.jpg", _make_image_bytes(), "image/jpeg")},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1
        assert data["results"][0]["id"] == str(product.id)


@pytest.mark.asyncio
async def test_visual_search_disabled_returns_503(client, db):
    await _auth_client(client, db, email="visualdisabled@test.com")
    visual_search_service._enabled = False
    response = await client.post(
        "/api/visual-search/",
        files={"image": ("query.jpg", _make_image_bytes(), "image/jpeg")},
    )
    assert response.status_code == 503
