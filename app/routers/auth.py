from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.services.auth0_service import auth0_service
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(request: Request):
    state = request.query_params.get("next", "/")
    return RedirectResponse(auth0_service.get_login_url(state))


@router.get("/callback")
async def callback(code: str, state: str = "/", db: AsyncSession = Depends(get_db)):
    try:
        token_data = await auth0_service.exchange_code(code)
        user_info = await auth0_service.get_user_info(token_data["access_token"])
        
        # Find or create user
        result = await db.execute(select(User).where(User.auth0_id == user_info["sub"]))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                auth0_id=user_info["sub"],
                email=user_info["email"],
                name=user_info.get("name"),
                picture=user_info.get("picture"),
            )
            db.add(user)
            await db.flush()
        
        # Set cookie with user ID (simplified - use JWT in production)
        response = RedirectResponse(state)
        response.set_cookie("user_id", str(user.id), httponly=True, secure=True)
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/logout")
async def logout():
    response = RedirectResponse(auth0_service.get_logout_url())
    response.delete_cookie("user_id")
    return response


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "loyalty_level": user.loyalty_level,
        "loyalty_points": user.loyalty_points,
        "total_spent": float(user.total_spent),
    }
