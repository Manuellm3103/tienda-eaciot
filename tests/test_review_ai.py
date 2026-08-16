import pytest
from sqlalchemy import select

from app.models.review import Review
from app.models.product import Product
from app.models.user import User
from app.services.review_ai_service import ReviewAIService
from app.services.auth_service import create_access_token


@pytest.fixture
def review_ai_service():
    return ReviewAIService()


class TestReviewAIService:
    @pytest.mark.asyncio
    async def test_sentiment_fallback_positive(self, review_ai_service):
        sentiment = await review_ai_service.analyze_sentiment("Great product", 5)
        assert sentiment["label"] == "positive"
        assert sentiment["score"] > 0

    @pytest.mark.asyncio
    async def test_sentiment_fallback_negative(self, review_ai_service):
        sentiment = await review_ai_service.analyze_sentiment("Terrible", 1)
        assert sentiment["label"] == "negative"
        assert sentiment["score"] < 0

    @pytest.mark.asyncio
    async def test_process_review_updates_model(
        self, db, review_ai_service
    ):
        user = User(email="u1@example.com", hashed_password="x", is_active=True)
        product = Product(title="P1", price=100, product_type="fisico")
        db.add(user)
        db.add(product)
        await db.flush()

        review = Review(
            user_id=user.id,
            product_id=product.id,
            rating=4,
            title="Good",
            comment="Nice quality",
        )
        db.add(review)
        await db.flush()

        result = await review_ai_service.process_review(db, review.id)
        assert result is not None
        assert result.sentiment_label in {"positive", "neutral", "negative"}
        assert result.sentiment_score is not None

    @pytest.mark.asyncio
    async def test_approve_and_reject_response(
        self, db, review_ai_service
    ):
        user = User(email="u2@example.com", hashed_password="x", is_active=True)
        product = Product(title="P2", price=100, product_type="fisico")
        db.add(user)
        db.add(product)
        await db.flush()

        review = Review(
            user_id=user.id,
            product_id=product.id,
            rating=5,
            comment="Excellent",
            ai_response="Thanks for your review!",
        )
        db.add(review)
        await db.flush()

        approved = await review_ai_service.approve_response(db, review.id)
        assert approved.ai_response_approved is True
        assert approved.ai_responded_at is not None

        rejected = await review_ai_service.reject_response(db, review.id)
        assert rejected.ai_response is None
        assert rejected.ai_response_approved is False


async def _auth_client(client, db, email: str = "reviewadmin@test.com", admin: bool = True) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, name="Review Admin", is_admin=admin)
        db.add(user)
    else:
        user.is_admin = admin
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": user.id})
    client.cookies.set("access_token", token)
    return user


@pytest.mark.asyncio
async def test_admin_reviews_page(client, db):
    admin = await _auth_client(client, db)
    user = User(
        email="reviewer@example.com",
        hashed_password="x",
        is_active=True,
    )
    product = Product(
        title="Test Product",
        price=100,
        product_type="fisico",
    )
    db.add(user)
    db.add(product)
    await db.flush()

    review = Review(
        user_id=user.id,
        product_id=product.id,
        rating=4,
        comment="Good product",
    )
    db.add(review)
    await db.commit()

    response = await client.get("/admin/reviews/")
    assert response.status_code == 200
    assert "Reseñas" in response.text or "Test Product" in response.text
