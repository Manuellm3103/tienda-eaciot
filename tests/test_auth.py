import pytest


async def _get_csrf(client) -> str:
    response = await client.get("/")
    return response.cookies.get("csrf_token", "")


@pytest.mark.asyncio
async def test_register_and_login(client):
    csrf = await _get_csrf(client)
    # Register
    response = await client.post("/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
        "_csrf_token": csrf,
    })
    assert response.status_code == 200
    
    # Login
    response = await client.post("/auth/login/web", json={
        "email": "test@example.com",
        "password": "password123",
        "_csrf_token": csrf,
    })
    assert response.status_code == 302
    assert "access_token" in response.cookies
