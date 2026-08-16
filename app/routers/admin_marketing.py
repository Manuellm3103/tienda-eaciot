from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.services.agents.marketing_orchestrator import marketing_orchestrator
from app.services.proactive_engine import proactive_engine
from app.templates_instance import templates


router = APIRouter(prefix="/admin/marketing", tags=["admin-marketing"])


@router.get("/")
async def marketing_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return templates.TemplateResponse(
        "admin/marketing.html",
        {"request": request},
    )


@router.post("/ask")
async def ask_marketing_agent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    body = await request.json()
    message = body.get("message", "")
    result = await marketing_orchestrator.run(db, message)
    return JSONResponse(
        {
            "answer": result.answer,
            "agent": result.agent_name,
            "metadata": result.metadata,
        }
    )


@router.post("/proactive/run")
async def run_proactive_engine(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    actions = await proactive_engine.run(db)
    return JSONResponse({"actions": actions})
