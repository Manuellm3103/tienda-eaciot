import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    # Register
    response = await client.post("/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    
    # Login
    response = await client.post("/auth/login/web", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 302
    assert "access_token" in response.cookies
