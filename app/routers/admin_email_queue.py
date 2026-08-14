from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.email_queue_service import email_queue_service
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/email-queue",
    tags=["admin-email-queue"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def email_queue_page(request: Request):
    return templates.TemplateResponse("admin/email_queue.html", {"request": request})


@router.get("/list")
async def email_queue_list(db: AsyncSession = Depends(get_db)):
    return JSONResponse({"emails": await email_queue_service.list_items(db)})


@router.post("/{email_id}/retry")
async def email_queue_retry(email_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    await validate_csrf(request)
    ok = await email_queue_service.retry_failed(db, email_id)
    await db.commit()
    return JSONResponse({"retried": ok})
