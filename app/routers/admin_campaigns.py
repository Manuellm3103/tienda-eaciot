from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.models.campaign import Campaign
from app.services.campaign_engine import campaign_engine
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/campaigns",
    tags=["admin-campaigns"],
    dependencies=[Depends(require_admin)],
)


class CreateCampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    campaign_type: str = Field(min_length=1, max_length=30)
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    segment: str = Field(default="all_active")


@router.get("/", response_class=HTMLResponse)
async def campaigns_page(
    request: Request, db: AsyncSession = Depends(get_db)
):
    campaigns = (
        await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    ).scalars().all()
    return templates.TemplateResponse(
        "admin/campaigns.html", {"request": request, "campaigns": campaigns}
    )


@router.get("/list")
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    campaigns = (
        await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    ).scalars().all()
    return {
        "campaigns": [
            {
                "id": str(c.id),
                "name": c.name,
                "type": c.type,
                "status": c.status,
                "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
                "executed_at": c.executed_at.isoformat() if c.executed_at else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in campaigns
        ]
    }


@router.post("/create")
async def create_campaign(
    request: Request,
    data: CreateCampaignRequest,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    campaign = Campaign(
        name=data.name,
        type=data.campaign_type,
        status="scheduled",
        target_audience={"segment": data.segment},
        content={"subject": data.subject, "body": data.body},
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return JSONResponse(
        {
            "id": str(campaign.id),
            "name": campaign.name,
            "type": campaign.type,
            "status": campaign.status,
        }
    )


@router.post("/{campaign_id}/run")
async def run_campaign(
    request: Request,
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        result = await campaign_engine.run_campaign(db, campaign_id)
        await db.commit()
        return JSONResponse(result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{campaign_id}/toggle")
async def toggle_campaign(
    request: Request,
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == "paused":
        campaign.status = "active"
    elif campaign.status in ("active", "scheduled"):
        campaign.status = "paused"
    else:
        raise HTTPException(
            status_code=400, detail="Cannot toggle completed/draft campaigns"
        )

    await db.commit()
    await db.refresh(campaign)
    return JSONResponse(
        {"id": str(campaign.id), "status": campaign.status}
    )
