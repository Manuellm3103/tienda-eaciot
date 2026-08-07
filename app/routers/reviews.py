from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.review_service import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewResponse)
async def create_review(data: ReviewCreate, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await review_service.create_review(db, UUID(user_id), data)


@router.get("/product/{product_id}", response_model=List[ReviewResponse])
async def get_product_reviews(product_id: UUID, db: AsyncSession = Depends(get_db)):
    return await review_service.get_product_reviews(db, product_id)


@router.get("/product/{product_id}/rating")
async def get_product_rating(product_id: UUID, db: AsyncSession = Depends(get_db)):
    return await review_service.get_product_rating(db, product_id)


@router.get("/me", response_model=List[ReviewResponse])
async def get_my_reviews(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await review_service.get_user_reviews(db, UUID(user_id))


@router.delete("/{review_id}")
async def delete_review(review_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    success = await review_service.delete_review(db, review_id, UUID(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return {"message": "Review deleted"}
