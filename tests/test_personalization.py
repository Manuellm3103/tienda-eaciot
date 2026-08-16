import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.product import Category, Product
from app.models.user_event import UserEvent
from app.services.auth_service import create_access_token
from app.services.personalization_service import personalization_service
from app.services.product_service import product_service
from app.schemas.product import ProductCreate


async def _auth_client(client, db, email: str = "personalization@test.com") -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Test User")
        db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


@pytest.mark.asyncio
async def test_personalization_cold_start_returns_trending(client, db):
    user = await _auth_client(client, db)

    category = Category(name="Cold", slug="cold")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    for i in range(3):
        db.add(
            Product(
                title=f"Trending {i}",
                description="Desc",
                price=10,
                category_id=category.id,
                product_type="fisico",
                stock=10,
            )
        )
    await db.commit()

    # No events for this user -> cold start should return trending.
    result = await personalization_service.recommend_for_user(db, str(user.id), n=5)
    assert result["personalized"] is False
    assert len(result["products"]) > 0


@pytest.mark.asyncio
async def test_personalization_boosts_favorite_category(client, db):
    user = await _auth_client(client, db)

    cat_a = Category(name="Cat A", slug="cat-a")
    cat_b = Category(name="Cat B", slug="cat-b")
    db.add_all([cat_a, cat_b])
    await db.commit()
    await db.refresh(cat_a)
    await db.refresh(cat_b)

    product_a = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto A",
            description="Desc",
            price=100,
            category_id=cat_a.id,
            product_type="fisico",
            stock=10,
        ),
    )
    product_b = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto B",
            description="Desc",
            price=100,
            category_id=cat_b.id,
            product_type="fisico",
            stock=10,
        ),
    )
    await db.commit()

    # Generate enough events in category A to make it the favorite.
    for _ in range(5):
        db.add(
            UserEvent(
                user_id=str(user.id),
                product_id=str(product_a.id),
                event_type="view",
            )
        )
    # One event in category B should not overcome category A.
    db.add(
        UserEvent(
            user_id=str(user.id),
            product_id=str(product_b.id),
            event_type="view",
        )
    )
    await db.commit()

    result = await personalization_service.recommend_for_user(db, str(user.id), n=5)
    assert result["personalized"] is True
    assert result["favorite_category_id"] == str(cat_a.id)
    # The top recommendation should be the product from the favorite category.
    assert result["products"][0].category_id == cat_a.id


@pytest.mark.asyncio
async def test_personalization_updates_user_favorite_category(client, db):
    user = await _auth_client(client, db)

    category = Category(name="Update", slug="update")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto Update",
            description="Desc",
            price=50,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        ),
    )
    await db.commit()

    for _ in range(5):
        db.add(
            UserEvent(
                user_id=str(user.id),
                product_id=str(product.id),
                event_type="view",
            )
        )
    await db.commit()

    await personalization_service.recommend_for_user(db, str(user.id), n=5)
    await db.refresh(user)
    assert user.favorite_category_id == str(category.id)


@pytest.mark.asyncio
async def test_personalization_excludes_purchased_products(client, db):
    user = await _auth_client(client, db)

    category = Category(name="Purchased", slug="purchased")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    product = await product_service.create_product(
        db,
        ProductCreate(
            title="Producto Comprado",
            description="Desc",
            price=50,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        ),
    )
    await db.commit()

    # User viewed the product and then purchased it.
    db.add(
        UserEvent(
            user_id=str(user.id),
            product_id=str(product.id),
            event_type="view",
        )
    )
    db.add(
        UserEvent(
            user_id=str(user.id),
            product_id=str(product.id),
            event_type="purchase",
        )
    )
    await db.commit()

    result = await personalization_service.recommend_for_user(db, str(user.id), n=5)
    recommended_ids = {p.id for p in result["products"]}
    assert product.id not in recommended_ids
