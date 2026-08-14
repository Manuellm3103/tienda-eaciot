from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_user_optional
from app.middleware import validate_csrf
from app.services.support_service import support_service
from app.templates_instance import templates

router = APIRouter(tags=["support"])


@router.get("/soporte", response_class=HTMLResponse)
async def support_form(request: Request):
    return templates.TemplateResponse("support.html", {"request": request})


@router.post("/soporte")
async def create_support_ticket(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    form = await request.form()
    email = (form.get("email") or "").strip()
    subject = (form.get("subject") or "").strip()
    message = (form.get("message") or "").strip()
    name = (form.get("name") or "").strip()

    if not email or not subject or not message:
        raise HTTPException(status_code=422, detail="email, asunto y mensaje son requeridos")

    user = await get_current_user_optional(request, db)
    await support_service.create_ticket(
        db,
        email=email,
        subject=subject,
        message=message,
        name=name or None,
        user_id=str(user.id) if user else None,
    )
    await db.commit()
    return RedirectResponse(url="/soporte?gracias=1", status_code=302)
