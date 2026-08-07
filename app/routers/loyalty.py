from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import get_db
from app.models.user import User
from app.services.loyalty_service import loyalty_service
from app.services.auth_service import decode_token

router = APIRouter(prefix="/loyalty", tags=["loyalty"])
templates = Jinja2Templates(directory="app/templates")


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


@router.get("/status")
async def get_loyalty_status(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = await _get_user_id(request, db)
    try:
        return await loyalty_service.get_user_loyalty(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/history")
async def get_loyalty_history(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = await _get_user_id(request, db)
    return await loyalty_service.get_loyalty_history(db, user_id)


@router.get("/", response_class=HTMLResponse)
async def loyalty_page(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        user_id = await _get_user_id(request, db)
        status = await loyalty_service.get_user_loyalty(db, user_id)
        history = await loyalty_service.get_loyalty_history(db, user_id)
    except HTTPException:
        return RedirectResponse(url="/auth/login?next=/loyalty/", status_code=302)
    return templates.TemplateResponse("loyalty.html", {"request": request, "status": status, "history": history})
