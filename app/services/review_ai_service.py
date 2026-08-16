"""AI review sentiment analysis and response generation.

Generates empathetic, brand-aligned public replies to customer reviews.
Best-effort: never blocks review creation if AI is unavailable.
"""
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.review import Review
from app.models.product import Product
from app.ai.ollama_client import OllamaClient


class ReviewAIService:
    """Analyze review sentiment and generate public responses."""

    def __init__(self) -> None:
        self.client = OllamaClient()

    def _sentiment_from_text(self, text: str | None, rating: int) -> dict[str, Any]:
        """Rule-based fallback sentiment when no LLM is available."""
        if rating >= 4:
            label = "positive"
            score = 0.6 + (rating - 4) * 0.2
        elif rating == 3:
            label = "neutral"
            score = 0.0
        else:
            label = "negative"
            score = -0.6 + (rating - 2) * 0.2
        return {"label": label, "score": round(max(-1.0, min(1.0, score)), 2)}

    async def analyze_sentiment(
        self,
        review_text: str | None,
        rating: int,
    ) -> dict[str, Any]:
        """Return sentiment label (-1..1) and score.

        Uses LLM when possible; falls back to rating-based heuristic.
        """
        if not self.client.host or not review_text:
            return self._sentiment_from_text(review_text, rating)

        prompt = (
            f"Analiza el sentimiento de esta reseña de producto. "
            f"Responde ÚNICAMENTE en JSON: {{\"label\": \"positive|neutral|negative\", "
            f"\"score\": float entre -1 y 1}}.\n\nReseña: {review_text}"
        )
        try:
            raw = await self.client.generate(
                prompt,
                system="Eres un analizador de sentimiento. Responde solo JSON válido.",
            )
            import json

            data = json.loads(raw.strip().split("\n")[-1])
            label = data.get("label", "neutral")
            score = float(data.get("score", 0.0))
            if label not in {"positive", "neutral", "negative"}:
                label = "neutral"
            return {"label": label, "score": round(max(-1.0, min(1.0, score)), 2)}
        except Exception:
            return self._sentiment_from_text(review_text, rating)

    async def generate_response(
        self,
        review: Review,
        product_name: str,
    ) -> str | None:
        """Generate a public reply to a review."""
        if not self.client.host:
            return None

        sentiment = review.sentiment_label or "neutral"
        prompt = (
            f"Escribe una respuesta pública cortés y profesional de la tienda "
            f"Tienda Eaciot a esta reseña de cliente. Sentimiento: {sentiment}.\n\n"
            f"Producto: {product_name}\n"
            f"Calificación: {review.rating}/5 estrellas\n"
            f"Título: {review.title or 'Sin título'}\n"
            f"Comentario: {review.comment or 'Sin comentario'}\n\n"
            f"Responde en primera persona del equipo de Tienda Eaciot, "
            f"agradeciendo oportunamente y ofreciendo una solución si la reseña es negativa. "
            f"Máximo 3 oraciones."
        )
        try:
            return await self.client.generate(
                prompt,
                system="Eres el community manager de Tienda Eaciot, amable y auténtico.",
            )
        except Exception:
            return None

    async def process_review(
        self,
        db: AsyncSession,
        review_id: str,
    ) -> Review | None:
        """Analyze sentiment and draft AI response for a review."""
        result = await db.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()
        if not review:
            return None

        sentiment = await self.analyze_sentiment(review.comment, review.rating)
        review.sentiment_score = sentiment["score"]
        review.sentiment_label = sentiment["label"]

        prod_result = await db.execute(
            select(Product.title).where(Product.id == review.product_id)
        )
        product_name = prod_result.scalar_one_or_none() or "tu producto"

        response = await self.generate_response(review, product_name)
        if response:
            review.ai_response = response

        await db.flush()
        return review

    async def approve_response(
        self,
        db: AsyncSession,
        review_id: str,
    ) -> Review | None:
        """Mark AI response as approved and published."""
        result = await db.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()
        if not review or not review.ai_response:
            return None
        review.ai_response_approved = True
        review.ai_responded_at = datetime.utcnow()
        await db.flush()
        return review

    async def reject_response(
        self,
        db: AsyncSession,
        review_id: str,
    ) -> Review | None:
        """Reject AI response so staff can write a manual one."""
        result = await db.execute(select(Review).where(Review.id == review_id))
        review = result.scalar_one_or_none()
        if not review:
            return None
        review.ai_response = None
        review.ai_response_approved = False
        await db.flush()
        return review


review_ai_service = ReviewAIService()
