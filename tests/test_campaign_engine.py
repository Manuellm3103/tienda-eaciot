import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models.user import User
from app.models.product import Category, Product
from app.models.order import Order
from app.models.user_event import UserEvent
from app.models.campaign import Campaign
from app.models.email_queue import EmailQueue
from app.services.campaign_engine import campaign_engine
from app.services.auth_service import create_access_token


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
async def test_create_seasonal_campaign(db):
    campaign = await campaign_engine.seasonal_campaign(db, "navidad")
    await db.commit()
    assert campaign is not None
    assert campaign.type == "seasonal"
    assert campaign.status == "scheduled"
    assert "navidad" in campaign.content.get("event", "")

    # Duplicate call should not create another campaign.
    campaign2 = await campaign_engine.seasonal_campaign(db, "navidad")
    assert campaign2 is None


@pytest.mark.asyncio
async def test_run_campaign_enqueues_email(db):
    user = User(email="campaign.user@test.com", name="Campaign User")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    campaign = Campaign(
        name="Gracias por tu compra",
        type="post_purchase",
        status="scheduled",
        target_audience={"user_id": user.id},
        content={
            "subject": "Gracias por tu compra",
            "body": "Esperamos que disfrutes tu pedido.",
        },
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    result = await campaign_engine.run_campaign(db, campaign.id)
    await db.commit()

    assert result["enqueued"] == 1
    queued = (
        await db.execute(
            select(EmailQueue).where(EmailQueue.to_email == user.email)
        )
    ).scalars().all()
    assert len(queued) == 1
    assert queued[0].subject == "Gracias por tu compra"

    updated = await db.get(Campaign, campaign.id)
    assert updated.status == "completed"
    assert updated.executed_at is not None


@pytest.mark.asyncio
async def test_abandoned_cart_creates_campaign(db):
    category = Category(name="Campaign Category", slug="campaign-category")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = Product(
        title="Campaign Product",
        description="x",
        price=25.00,
        stock=10,
        category_id=category.id,
        product_type="fisico",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    user = User(email="abandoned.campaign@test.com", name="Abandoned")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    db.add(UserEvent(event_type="cart_add", user_id=user.id, product_id=product.id))
    await db.commit()

    result = await campaign_engine.detect_abandoned_carts(db)
    await db.commit()

    assert result["campaigns_created"] >= 1
    campaigns = (
        await db.execute(
            select(Campaign)
            .where(Campaign.type == "abandoned_cart")
            .where(Campaign.target_audience["user_id"].as_string() == user.id)
        )
    ).scalars().all()
    assert len(campaigns) >= 1

    queued = (
        await db.execute(
            select(EmailQueue).where(EmailQueue.to_email == user.email)
        )
    ).scalars().all()
    assert len(queued) >= 1


@pytest.mark.asyncio
async def test_on_order_placed_schedules_follow_ups(db):
    user = User(email="order.campaigns@test.com", name="Order Campaigns")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    order = Order(
        user_id=user.id,
        subtotal=100.00,
        total_amount=116.00,
        status="paid",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    await campaign_engine.on_order_placed(db, order)
    await db.commit()

    campaigns = (
        await db.execute(
            select(Campaign).where(Campaign.target_audience["order_id"].as_string() == order.id)
        )
    ).scalars().all()
    types = {c.type for c in campaigns}
    assert {"post_purchase", "cross_sell", "review_request"}.issubset(types)
    for c in campaigns:
        assert c.scheduled_at is not None
        assert c.status == "scheduled"


@pytest.mark.asyncio
async def test_admin_campaigns_page_requires_admin(client):
    response = await client.get("/admin/campaigns/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_campaigns_dashboard(client, db):
    await _auth_admin(client, db)
    response = await client.get("/admin/campaigns/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_run_campaign(client, db):
    await _auth_admin(client, db)

    user = User(email="admin.run@test.com", name="Admin Run")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    campaign = Campaign(
        name="Test Campaign",
        type="post_purchase",
        status="scheduled",
        target_audience={"user_id": user.id},
        content={"subject": "Hola", "body": "Mundo"},
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    # Load a page so the CSRF middleware sets the cookie.
    await client.get("/admin/campaigns/")
    csrf = next(
        (c.value for c in client.cookies.jar if c.name == "csrf_token"), None
    )
    assert csrf, "CSRF cookie was not set by middleware"
    response = await client.post(
        f"/admin/campaigns/{campaign.id}/run",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json()["enqueued"] == 1
