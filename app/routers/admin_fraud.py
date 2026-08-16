from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.fraud_score import FraudScore
from app.models.order import Order
from app.models.user import User
from app.templates_instance import templates


router = APIRouter(prefix="/admin/fraud", tags=["admin-fraud"])


@router.get("/")
async def fraud_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    scores = (
        await db.execute(
            select(FraudScore, Order)
            .join(Order, FraudScore.order_id == Order.id)
            .order_by(FraudScore.created_at.desc())
            .limit(100)
        )
    ).all()

    items = []
    for score, order in scores:
        user = await db.get(User, str(order.user_id)) if order.user_id else None
        items.append(
            {
                "id": str(score.id),
                "order_id": str(score.order_id),
                "risk_score": score.risk_score,
                "risk_level": score.risk_level,
                "auto_decision": score.auto_decision,
                "flags": score.flags_json,
                "customer_email": user.email if user else "",
                    "total": float(order.total_amount) if order.total_amount else 0,
                "created_at": score.created_at.isoformat() if score.created_at else None,
            }
        )

    return templates.TemplateResponse(
        "admin/fraud.html",
        {"request": request, "scores": items},
    )


@router.post("/{score_id}/review")
async def review_fraud_score(
    score_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    score = await db.get(FraudScore, score_id)
    if not score:
        raise HTTPException(status_code=404, detail="Not found")
    score.reviewed_by = str(admin.id)
    await db.flush()
    return JSONResponse({"status": "reviewed"})
