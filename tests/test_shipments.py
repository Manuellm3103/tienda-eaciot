import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.order import Order
from app.models.shipping import Shipment
from app.services.auth_service import create_access_token
from app.services.shipping_service import shipping_service


async def _auth_admin(client, db):
    result = await db.execute(select(User).where(User.email == "admin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admin@test.com", name="Admin", is_admin=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


@pytest.mark.asyncio
async def test_shipments_page_requires_admin(client):
    resp = await client.get("/admin/shipments/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_assign_tracking_generates_url(client, db):
    await _auth_admin(client, db)

    user = User(email="ship1@test.com", name="Ship")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    order = Order(user_id=user.id, subtotal=10, total_amount=10)
    db.add(order)
    await db.commit()
    await db.refresh(order)

    shipment = Shipment(order_id=order.id, carrier="pending", shipping_cost=0)
    db.add(shipment)
    await db.commit()
    await db.refresh(shipment)

    csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)
    # Trigger middleware to emit a CSRF cookie if not present yet.
    if not csrf:
        await client.get("/admin/shipments/")
        csrf = next((c.value for c in client.cookies.jar if c.name == "csrf_token"), None)

    resp = await client.post(
        f"/admin/shipments/{shipment.id}/assign",
        json={"carrier": "fedex", "tracking_number": "12345"},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert "fedex" in resp.json()["tracking_url"]

    await db.refresh(shipment)
    assert shipment.carrier == "fedex"
    assert shipment.tracking_number == "12345"
