from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.models.review import Review
from app.schemas.review import ReviewResponse
from app.services.review_ai_service import review_ai_service
from app.middleware import validate_csrf
from app.templates_instance import templates
from sqlalchemy import select

router = APIRouter(prefix="/admin/reviews", tags=["admin", "reviews"])


@router.get("/", response_class=HTMLResponse)
async def reviews_admin_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Render the AI review moderation page."""
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.product))
        .order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    return templates.TemplateResponse(
        "admin/reviews.html",
        {"request": request, "reviews": reviews},
    )


@router.get("/api", response_model=List[ReviewResponse])
async def list_reviews_for_moderation(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """List all reviews pending AI response or moderation (API)."""
    result = await db.execute(
        select(Review).order_by(Review.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{review_id}/generate-response")
async def generate_review_response(
    review_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await validate_csrf(request)
    review = await review_ai_service.process_review(db, str(review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return {
        "sentiment": review.sentiment_label,
        "score": review.sentiment_score,
        "ai_response": review.ai_response,
    }


@router.post("/{review_id}/approve-response")
async def approve_review_response(
    review_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await validate_csrf(request)
    review = await review_ai_service.approve_response(db, str(review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found or no AI response")
    return {"message": "AI response approved", "ai_response": review.ai_response}


@router.post("/{review_id}/reject-response")
async def reject_review_response(
    review_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    await validate_csrf(request)
    review = await review_ai_service.reject_response(db, str(review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "AI response rejected"}
