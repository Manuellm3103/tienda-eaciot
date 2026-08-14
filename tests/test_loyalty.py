import pytest
from uuid import UUID
from decimal import Decimal
from app.services.loyalty_service import loyalty_service
from app.models.user import User
from app.services.auth_service import create_access_token


def test_calculate_level():
    assert loyalty_service.calculate_level(Decimal("0")) == "bronce"
    assert loyalty_service.calculate_level(Decimal("500")) == "plata"
    assert loyalty_service.calculate_level(Decimal("1500")) == "oro"
    assert loyalty_service.calculate_level(Decimal("5000")) == "diamante"


def test_get_discount():
    assert loyalty_service.get_discount("bronce") == 5
    assert loyalty_service.get_discount("plata") == 10
    assert loyalty_service.get_discount("oro") == 15
    assert loyalty_service.get_discount("diamante") == 20


@pytest.mark.asyncio
async def test_get_user_loyalty_accepts_uuid_object(db):
    """Regression: PKs are String(36); binding a UUID object to db.get() raises
    sqlite3.ProgrammingError, which turned GET /loyalty/ into a 500 for every
    customer. The service must coerce user_id to str."""
    user = User(email="loyal.uuid@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    status = await loyalty_service.get_user_loyalty(db, UUID(user.id))
    assert status["level"] == "bronce"
    assert status["points"] == 0


@pytest.mark.asyncio
async def test_get_loyalty_history_accepts_uuid_object(db):
    user = User(email="loyal.uuid.history@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    history = await loyalty_service.get_loyalty_history(db, UUID(user.id))
    assert history == []


@pytest.mark.asyncio
async def test_loyalty_page_returns_200_for_authed_customer(client, db):
    """Endpoint-level regression: GET /loyalty/ must render 200 for a real
    authenticated customer (was a 500 due to UUID binding in the service)."""
    user = User(email="loyal.page@test.com")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    client.cookies.set("access_token", create_access_token({"sub": str(user.id)}))
    resp = await client.get("/loyalty/")
    assert resp.status_code == 200
