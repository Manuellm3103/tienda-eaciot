from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from decimal import Decimal
from datetime import datetime
from app.database import get_db
from app.models.promotion import Promotion
from app.schemas.promotion import PromotionCreate, PromotionResponse, CongratulationRuleCreate, CongratulationRuleResponse
from app.services.promotion_service import promotion_service

router = APIRouter(prefix="/admin/promotions", tags=["admin-promotions"])
templates = Jinja2Templates(directory="app/templates")


@router.post("/", response_model=PromotionResponse)
async def create_promotion(data: PromotionCreate, db: AsyncSession = Depends(get_db)):
    return await promotion_service.create_promotion(db, data)


@router.post("/{promotion_id}/approve", response_model=PromotionResponse)
async def approve_promotion(promotion_id: UUID, db: AsyncSession = Depends(get_db)):
    promotion = await promotion_service.approve_promotion(db, promotion_id)
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return promotion


@router.post("/congratulations/rules/", response_model=CongratulationRuleResponse)
async def create_congratulation_rule(data: CongratulationRuleCreate, db: AsyncSession = Depends(get_db)):
    return await promotion_service.create_congratulation_rule(db, data)


@router.get("/congratulations/rules/")
async def list_congratulation_rules(db: AsyncSession = Depends(get_db)):
    return await promotion_service.get_congratulation_rules(db)


# ==================== HTML ADMIN PAGES ====================

@router.get("/", response_class=HTMLResponse)
async def admin_promotions_list(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Promotion).order_by(Promotion.created_at.desc()))
    promotions = result.scalars().all()
    return templates.TemplateResponse("admin/promotions.html", {"request": request, "promotions": promotions})


@router.get("/new", response_class=HTMLResponse)
async def admin_promotion_new(request: Request):
    return templates.TemplateResponse("admin/promotion_form.html", {"request": request, "promotion": None})


@router.post("/new")
async def admin_promotion_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    discount_type: str = Form(...),
    discount_value: str = Form(...),
    coupon_code: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    data = PromotionCreate(
        title=title,
        description=description or None,
        discount_type=discount_type,
        discount_value=Decimal(discount_value),
        coupon_code=coupon_code or None,
    )
    await promotion_service.create_promotion(db, data)
    await db.commit()
    return RedirectResponse(url="/admin/promotions/", status_code=302)


@router.get("/{promotion_id}/approve")
async def admin_promotion_approve(promotion_id: str, db: AsyncSession = Depends(get_db)):
    await promotion_service.approve_promotion(db, promotion_id)
    await db.commit()
    return RedirectResponse(url="/admin/promotions/", status_code=302)


@router.post("/{promotion_id}/delete")
async def admin_promotion_delete(promotion_id: str, db: AsyncSession = Depends(get_db)):
    promo = await db.get(Promotion, promotion_id)
    if promo:
        await db.delete(promo)
        await db.commit()
    return RedirectResponse(url="/admin/promotions/", status_code=302)
