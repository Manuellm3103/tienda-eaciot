import pytest


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
