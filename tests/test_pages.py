import pytest
from sqlalchemy import select
from app.models.product import Product, Category
from app.models.user import User
from app.services.auth_service import create_access_token


async def _authenticate_admin(client, db) -> None:
    """Ensure an admin user exists and attach a valid access_token cookie."""
    result = await db.execute(select(User).where(User.email == "admin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admin@test.com", name="Admin", is_admin=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_homepage(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Tienda Eaciot" in response.text


@pytest.mark.asyncio
async def test_assetlinks_for_android_twa(client):
    """La TWA de Android necesita /.well-known/assetlinks.json para verificarse."""
    response = await client.get("/.well-known/assetlinks.json")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["relation"] == ["delegate_permission/common.handle_all_urls"]
    assert data[0]["target"]["namespace"] == "android_app"
    assert data[0]["target"]["package_name"] == "com.eaciot.twa"


@pytest.mark.asyncio
async def test_products_page(client):
    response = await client.get("/products/")
    assert response.status_code == 200
    assert "Productos" in response.text


@pytest.mark.asyncio
async def test_login_page(client):
    response = await client.get("/auth/login")
    assert response.status_code == 200
    assert "Iniciar Sesión" in response.text


@pytest.mark.asyncio
async def test_register_page(client):
    response = await client.get("/auth/register")
    assert response.status_code == 200
    assert "Crear Cuenta" in response.text


@pytest.mark.asyncio
async def test_cart_page(client):
    response = await client.get("/cart")
    assert response.status_code == 200
    assert "Carrito" in response.text


@pytest.mark.asyncio
async def test_checkout_redirects_when_not_logged_in(client):
    response = await client.get("/checkout")
    assert response.status_code == 302
    assert response.headers["location"] == "/products/"


@pytest.mark.asyncio
async def test_admin_dashboard_page(client, db):
    await _authenticate_admin(client, db)
    response = await client.get("/admin/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text


@pytest.mark.asyncio
async def test_admin_products_page(client, db):
    await _authenticate_admin(client, db)
    response = await client.get("/admin/products/")
    assert response.status_code == 200
    assert "Administrar Productos" in response.text


@pytest.mark.asyncio
async def test_api_products_returns_json(client):
    response = await client.get("/api/products/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_cart_add_get_fallback(client, db):
    category = Category(name="Test Category", slug="test-category")
    db.add(category)
    await db.commit()
    await db.refresh(category)
    product = Product(
        title="Test Product",
        description="A test product",
        price=10.00,
        stock=5,
        category_id=category.id,
        product_type="fisico",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    response = await client.get(f"/cart/add/{product.id}")
    assert response.status_code == 302
    assert response.headers["location"] == "/cart"
    print("Set-Cookie:", response.headers.get("set-cookie"))
    # Follow the redirect to confirm the cookie was persisted.
    follow = await client.get(response.headers["location"])
    assert follow.status_code == 200
    cart_cookie = next((c for c in client.cookies.jar if c.name == "cart"), None)
    assert cart_cookie is not None

    # The cart cookie is base64(urlsafe) JSON — decode it back.
    import base64
    import json

    raw = cart_cookie.value
    decoded = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
    assert json.loads(decoded) == {str(product.id): 1}
