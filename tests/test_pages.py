import pytest
from app.models.product import Product, Category


@pytest.mark.asyncio
async def test_homepage(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "Tienda Eaciot" in response.text


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
async def test_admin_dashboard_page(client):
    response = await client.get("/admin/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text


@pytest.mark.asyncio
async def test_admin_products_page(client):
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
    import json

    # HTTPX may preserve the cookie value as a JSON-encoded string literal.
    raw = cart_cookie.value
    if isinstance(raw, str) and raw.startswith('"') and raw.endswith('"'):
        raw = json.loads(raw)
    assert json.loads(raw) == {str(product.id): 1}
