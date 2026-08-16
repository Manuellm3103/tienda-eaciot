from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/whatsapp",
    tags=["admin-whatsapp"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def whatsapp_admin_page(
    request: Request, db: AsyncSession = Depends(get_db)
):
    """Admin dashboard for WhatsApp commerce stats."""
    whatsapp_users = (
        await db.execute(
            select(User).where(User.phone.isnot(None)).order_by(User.created_at.desc())
        )
    ).scalars().all()

    return templates.TemplateResponse(
        "admin/whatsapp.html",
        {
            "request": request,
            "whatsapp_users": whatsapp_users,
            "webhook_url": f"{request.base_url}webhooks/whatsapp",
        },
    )
