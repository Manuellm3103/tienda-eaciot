import pytest
from app.models.product import Product, Category
from app.models.user_event import UserEvent
from app.services.recommendation_service import recommendation_service


@pytest.mark.asyncio
async def test_trending_ranks_by_demand(db):
    category = Category(name="Rec Cat", slug="rec-cat")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    hot = Product(title="Hot Product", description="demo", price=10, stock=5, category_id=category.id, product_type="fisico")
    warm = Product(title="Warm Product", description="demo", price=20, stock=5, category_id=category.id, product_type="fisico")
    cold = Product(title="Cold Product", description="demo", price=30, stock=5, category_id=category.id, product_type="fisico")
    db.add_all([hot, warm, cold])
    await db.commit()
    for p in (hot, warm, cold):
        await db.refresh(p)

    for _ in range(3):
        db.add(UserEvent(event_type="view", product_id=hot.id))
    db.add(UserEvent(event_type="view", product_id=warm.id))
    await db.commit()

    trending = await recommendation_service.get_trending(db, limit=2)
    assert trending[0].id == hot.id


@pytest.mark.asyncio
async def test_related_uses_session_cooccurrence(db):
    category = Category(name="Rec Cat 2", slug="rec-cat-2")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    source = Product(title="Source", description="demo", price=10, stock=5, category_id=category.id, product_type="fisico")
    mate = Product(title="Mate", description="demo", price=20, stock=5, category_id=category.id, product_type="fisico")
    stranger = Product(title="Stranger", description="demo", price=30, stock=5, category_id=category.id, product_type="fisico")
    db.add_all([source, mate, stranger])
    await db.commit()
    for p in (source, mate, stranger):
        await db.refresh(p)

    db.add(UserEvent(event_type="view", product_id=source.id, session_id="sess-1"))
    db.add(UserEvent(event_type="view", product_id=mate.id, session_id="sess-1"))
    await db.commit()

    related = await recommendation_service.get_related(db, source.id, limit=4)
    related_ids = [p.id for p in related]
    assert mate.id in related_ids
