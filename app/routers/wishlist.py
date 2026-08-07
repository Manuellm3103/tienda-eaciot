from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.database import get_db
from app.schemas.product import ProductResponse
from app.services.wishlist_service import wishlist_service

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("/", response_model=List[ProductResponse])
async def get_wishlist(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return await wishlist_service.get_wishlist(db, UUID(user_id))


@router.post("/{product_id}")
async def add_to_wishlist(product_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    added = await wishlist_service.add_to_wishlist(db, UUID(user_id), product_id)
    if not added:
        raise HTTPException(status_code=400, detail="Product already in wishlist")
    
    return {"message": "Added to wishlist"}


@router.delete("/{product_id}")
async def remove_from_wishlist(product_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    removed = await wishlist_service.remove_from_wishlist(db, UUID(user_id), product_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Product not in wishlist")
    
    return {"message": "Removed from wishlist"}


@router.get("/check/{product_id}")
async def check_wishlist(product_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return {"in_wishlist": False}
    
    is_in = await wishlist_service.is_in_wishlist(db, UUID(user_id), product_id)
    return {"in_wishlist": is_in}
