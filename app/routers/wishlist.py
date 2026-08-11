from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.schemas.product import ProductResponse
from app.services.wishlist_service import wishlist_service
from app.services.auth_service import decode_token
from app.middleware import validate_csrf

router = APIRouter(prefix="/wishlist", tags=["wishlist"])
from app.templates_instance import templates


async def _get_user_id(request: Request, db: AsyncSession) -> UUID:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UUID(user_id)


@router.get("/", response_model=List[ProductResponse])
async def get_wishlist(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = await _get_user_id(request, db)
    return await wishlist_service.get_wishlist(db, user_id)


@router.post("/{product_id}")
async def add_to_wishlist(product_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    await validate_csrf(request)
    user_id = await _get_user_id(request, db)
    added = await wishlist_service.add_to_wishlist(db, user_id, product_id)
    if not added:
        raise HTTPException(status_code=400, detail="Product already in wishlist")
    return {"message": "Added to wishlist"}


@router.delete("/{product_id}")
async def remove_from_wishlist(product_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    await validate_csrf(request)
    user_id = await _get_user_id(request, db)
    removed = await wishlist_service.remove_from_wishlist(db, user_id, product_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Product not in wishlist")
    return {"message": "Removed from wishlist"}


@router.get("/check/{product_id}")
async def check_wishlist(product_id: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user_id = await _get_user_id(request, db)
        is_in = await wishlist_service.is_in_wishlist(db, user_id, product_id)
        return {"in_wishlist": is_in}
    except HTTPException:
        return {"in_wishlist": False}


# ==================== HTML PAGE ====================

@router.get("/page", response_class=HTMLResponse)
async def wishlist_page(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user_id = await _get_user_id(request, db)
        products = await wishlist_service.get_wishlist(db, user_id)
    except HTTPException:
        return RedirectResponse(url="/auth/login?next=/wishlist/page", status_code=302)
    return templates.TemplateResponse("wishlist.html", {"request": request, "products": products})
