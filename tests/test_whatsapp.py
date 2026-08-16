import pytest
from sqlalchemy import select
from unittest.mock import AsyncMock, patch

from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.whatsapp_service import whatsapp_service


async def _auth_admin(client, db) -> None:
    result = await db.execute(select(User).where(User.email == "admin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admin@test.com", name="Admin", is_admin=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        user.is_admin = True
        await db.commit()
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_whatsapp_webhook_verification(client):
    response = await client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_verify_token",
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 403

    with patch("app.routers.webhooks.settings.whatsapp_verify_token", "test_verify_token"):
        response = await client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "12345",
            },
        )
    assert response.status_code == 200
    assert response.text == "12345"


@pytest.mark.asyncio
async def test_whatsapp_incoming_message_creates_user_and_enqueues_reply(client, db):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "521234567890",
                                    "id": "wamid.test",
                                    "type": "text",
                                    "text": {"body": "Hola, tienen tenis?"},
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }

    with patch.object(
        whatsapp_service, "_send_whatsapp_reply", new=AsyncMock()
    ) as mock_send:
        with patch(
            "app.services.whatsapp_service.chat_service.chat",
            new=AsyncMock(return_value={"answer": "Sí, tenemos varios modelos.", "products": []}),
        ):
            response = await client.post("/webhooks/whatsapp", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    user = (
        await db.execute(select(User).where(User.phone == "521234567890"))
    ).scalar_one_or_none()
    assert user is not None
    assert user.email.startswith("whatsapp+")
    mock_send.assert_awaited_once()


@pytest.mark.asyncio
async def test_whatsapp_service_formats_reply_with_products():
    products = [
        {"id": "p1", "title": "Tenis Nike", "price": 1500.00},
    ]
    text = whatsapp_service._format_reply("Sí tenemos", products)
    assert "Sí tenemos" in text
    assert "Tenis Nike" in text
    assert "$1500.00" in text


@pytest.mark.asyncio
async def test_admin_whatsapp_page_requires_admin(client):
    response = await client.get("/admin/whatsapp/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_whatsapp_page(client, db):
    await _auth_admin(client, db)
    response = await client.get("/admin/whatsapp/")
    assert response.status_code == 200
