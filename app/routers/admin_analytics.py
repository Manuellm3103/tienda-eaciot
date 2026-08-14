from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.database import get_db
from app.dependencies import require_admin
from app.services.ai_analytics import ai_analytics
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin-analytics"],
    dependencies=[Depends(require_admin)],
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@router.get("/", response_class=HTMLResponse)
async def analytics_page(request: Request):
    return templates.TemplateResponse(
        "admin/analytics.html", {"request": request}
    )


@router.post("/ask")
async def ask(
    request: Request,
    data: QuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await ai_analytics.answer_question(db, data.question)
    return JSONResponse(result)
