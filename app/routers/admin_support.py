from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.support_service import support_service
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/support",
    tags=["admin-support"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def support_page(request: Request):
    return templates.TemplateResponse("admin/support.html", {"request": request})


@router.get("/list")
async def list_tickets(status: str = None, db: AsyncSession = Depends(get_db)):
    tickets = await support_service.list_tickets(db, status)
    return JSONResponse(
        {
            "tickets": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "email": t.email,
                    "subject": t.subject,
                    "message": t.message[:500],
                    "status": t.status,
                    "admin_notes": t.admin_notes,
                    "created_at": t.created_at.isoformat() if t.created_at else "",
                }
                for t in tickets
            ]
        }
    )


@router.post("/{ticket_id}/status")
async def update_status(
    ticket_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    body = await request.json()
    status = body.get("status")
    if status not in ("open", "in_progress", "resolved", "closed"):
        raise HTTPException(status_code=422, detail="estado inválido")
    ticket = await support_service.update_status(
        db, ticket_id, status, admin_notes=body.get("admin_notes")
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    await db.commit()
    return JSONResponse({"status": ticket.status})
