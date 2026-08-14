import pytest
from sqlalchemy import select
from app.models.product import Product, Category
from app.models.user import User
from app.models.user_event import UserEvent
from app.models.email_queue import EmailQueue
from app.services.auth_service import create_access_token


async def _auth_admin(client, db) -> None:
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
async def test_cart_recovery_page_requires_admin(client):
    response = await client.get("/admin/cart-recovery/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cart_recovery_candidates_and_send(client, db):
    await _auth_admin(client, db)

    category = Category(name="Recovery Category", slug="recovery-category")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Recovery Product",
        description="x",
        price=10.00,
        stock=5,
        category_id=category.id,
        product_type="fisico",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    user = User(email="shopper.cart.recovery@test.com", name="Shopper")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    db.add(UserEvent(event_type="cart_add", user_id=user.id, product_id=product.id))
    await db.commit()

    resp = await client.get("/admin/cart-recovery/candidates")
    assert resp.status_code == 200
    emails = [c["email"] for c in resp.json()["candidates"]]
    assert "shopper.cart.recovery@test.com" in emails

    # Send recovery using the CSRF cookie the middleware emitted on the GET.
    csrf = next(
        (c.value for c in client.cookies.jar if c.name == "csrf_token"), None
    )
    assert csrf, "CSRF cookie was not set by middleware"
    resp = await client.post(
        "/admin/cart-recovery/send",
        json={"user_ids": [user.id]},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    assert resp.json()["enqueued"] == 1

    queued = (
        await db.execute(
            select(EmailQueue).where(EmailQueue.to_email == user.email)
        )
    ).scalars().all()
    assert len(queued) == 1
    assert queued[0].subject.startswith("🧺 ")
    assert "Recovery Product" in queued[0].html_content
