from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.abandoned_cart_service import abandoned_cart_service
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/cart-recovery",
    tags=["admin-cart-recovery"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def cart_recovery_page(request: Request):
    return templates.TemplateResponse(
        "admin/cart_recovery.html", {"request": request}
    )


@router.get("/candidates")
async def cart_recovery_candidates(db: AsyncSession = Depends(get_db)):
    candidates = await abandoned_cart_service.get_candidates(db)
    return JSONResponse({"candidates": candidates})


@router.post("/send")
async def cart_recovery_send(request: Request, db: AsyncSession = Depends(get_db)):
    """Draft + enqueue recovery emails. Delivery is handled by the cron worker."""
    await validate_csrf(request)
    body = await request.json()
    user_ids = body.get("user_ids")
    send_all = bool(body.get("all", False))
    result = await abandoned_cart_service.enqueue_recovery_emails(
        db, user_ids=None if send_all else user_ids
    )
    return JSONResponse(result)
