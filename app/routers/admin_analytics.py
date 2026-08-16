import io
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.database import get_db
from app.dependencies import require_admin
from app.models.saved_report import SavedReport
from app.services.ai_analytics import ai_analytics
from app.services.chart_service import chart_service
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin-analytics"],
    dependencies=[Depends(require_admin)],
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class SaveReportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    question: str = Field(min_length=3, max_length=500)
    sql: str = Field(min_length=1)
    chart_type: str = Field(default="table")


@router.get("/", response_class=HTMLResponse)
async def analytics_page(request: Request, db: AsyncSession = Depends(get_db)):
    reports = (await db.execute(select(SavedReport).order_by(SavedReport.created_at.desc()))).scalars().all()
    return templates.TemplateResponse(
        "admin/analytics.html", {"request": request, "saved_reports": reports}
    )


@router.post("/ask")
async def ask(
    request: Request,
    data: QuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await ai_analytics.answer_question(db, data.question)
    return JSONResponse(result)


@router.post("/chart")
async def chart(
    request: Request,
    data: QuestionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Answer the question and return a rendered chart image."""
    result = await ai_analytics.answer_question(db, data.question)
    if result.get("error"):
        return JSONResponse(result, status_code=400)

    try:
        image = chart_service.render(
            result.get("chart_type", "table"),
            result.get("columns", []),
            result.get("data", []),
        )
    except RuntimeError as exc:
        return JSONResponse({"error": str(exc)}, status_code=503)
    except Exception as exc:
        return JSONResponse({"error": f"Chart failed: {exc}"}, status_code=500)

    return StreamingResponse(
        io.BytesIO(image),
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="chart.png"'},
    )


@router.get("/reports")
async def list_saved_reports(db: AsyncSession = Depends(get_db)):
    reports = (await db.execute(select(SavedReport).order_by(SavedReport.created_at.desc()))).scalars().all()
    return {
        "reports": [
            {
                "id": str(r.id),
                "name": r.name,
                "question": r.question,
                "chart_type": r.chart_type,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ]
    }


@router.post("/reports")
async def save_report(
    request: Request,
    data: SaveReportRequest,
    db: AsyncSession = Depends(get_db),
):
    report = SavedReport(
        name=data.name,
        question=data.question,
        sql=data.sql,
        chart_type=data.chart_type,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return JSONResponse({
        "id": str(report.id),
        "name": report.name,
        "question": report.question,
        "chart_type": report.chart_type,
    })


@router.post("/reports/{report_id}/run")
async def run_saved_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    report = await db.get(SavedReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    result = await ai_analytics.answer_question(db, report.question)
    return JSONResponse(result)
