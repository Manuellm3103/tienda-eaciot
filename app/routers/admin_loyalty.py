from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services.ai_loyalty_service import ai_loyalty_service
from app.templates_instance import templates


router = APIRouter(prefix="/admin/loyalty", tags=["admin-loyalty"])


@router.get("/")
async def admin_loyalty_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        "admin/loyalty.html",
        {"request": request},
    )


@router.get("/at-risk")
async def at_risk_customers(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Return customers with medium/high churn risk and suggested offers."""
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()
    at_risk = []
    for user in users:
        risk = await ai_loyalty_service.predict_churn_risk(db, str(user.id))
        if risk["level"] in ("medium", "high"):
            offer = await ai_loyalty_service.suggest_retention_offer(db, str(user.id))
            at_risk.append(
                {
                    "user_id": str(user.id),
                    "email": user.email,
                    "name": user.name,
                    "risk_level": risk["level"],
                    "risk_score": risk["score"],
                    "days_since_last_purchase": risk["days_since_last_purchase"],
                    "offer": offer,
                }
            )
    return JSONResponse(at_risk)


@router.get("/birthdays")
async def birthday_campaign(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    offers = await ai_loyalty_service.generate_birthday_campaign(db)
    return JSONResponse(offers)


@router.post("/users/{user_id}/quest")
async def create_quest(
    user_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    body = await request.json()
    quest = await ai_loyalty_service.create_quest(
        db,
        user_id,
        quest_type=body["quest_type"],
        target=body["target"],
        reward_type=body["reward_type"],
        reward_value=body["reward_value"],
        expires_days=body.get("expires_days"),
    )
    return JSONResponse(
        {
            "id": str(quest.id),
            "quest_type": quest.quest_type,
            "target": quest.target,
            "reward_type": quest.reward_type,
            "reward_value": quest.reward_value,
        }
    )
