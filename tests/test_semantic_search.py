import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import select

from app.models.user import User
from app.models.product import Category, Product
from app.services.auth_service import create_access_token
from app.services.semantic_search_service import SemanticSearchService


async def _auth_admin(client, db) -> None:
    result = await db.execute(select(User).where(User.email == "admin@test.com"))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email="admin@test.com", name="Admin", is_admin=True)
        db.add(user)
    else:
        user.is_admin = True
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_semantic_search_dashboard_requires_admin(client, db):
    response = await client.get("/admin/search/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_semantic_search_reindex_with_mocked_meilisearch(client, db):
    await _auth_admin(client, db)

    category = Category(name="Search", slug="search")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    db.add(
        Product(
            title="Zapatos",
            description="Zapatos deportivos",
            price=100,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        )
    )
    await db.commit()

    fake_index = MagicMock()
    fake_client = MagicMock()
    fake_client.index.return_value = fake_index
    fake_client.get_indexes.return_value = {"results": []}

    service = SemanticSearchService()
    service._client = fake_client

    count = await service.index_products(db)
    assert count >= 1
    fake_client.create_index.assert_called_once()
    fake_index.add_documents.assert_called_once()


@pytest.mark.asyncio
async def test_semantic_search_sql_fallback(client, db):
    category = Category(name="Fallback", slug="fallback")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    db.add(
        Product(
            title="Camisa",
            description="Camisa de algodón",
            price=200,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        )
    )
    await db.commit()

    service = SemanticSearchService()
    service._client = None

    result = await service.search(db, query="Camisa", limit=10)
    assert result["source"] == "sql"
    assert result["total"] >= 1


@pytest.mark.asyncio
async def test_semantic_search_stats(client, db):
    await _auth_admin(client, db)
    response = await client.get("/admin/search/stats")
    assert response.status_code == 200
    data = response.json()
    assert "facets" in data
    assert "enabled" in data
