from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.models.supplier import Supplier
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/suppliers",
    tags=["admin-suppliers"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def suppliers_list(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Supplier).order_by(Supplier.name))
    suppliers = result.scalars().all()
    return templates.TemplateResponse(
        "admin/suppliers.html",
        {"request": request, "suppliers": suppliers},
    )


@router.post("/")
async def supplier_create(
    request: Request,
    name: str = Form(...),
    contact_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    website: str = Form(""),
    lead_time_days: int = Form(0),
    notes: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    db.add(Supplier(
        name=name.strip(),
        contact_name=contact_name.strip() or None,
        email=email.strip() or None,
        phone=phone.strip() or None,
        website=website.strip() or None,
        lead_time_days=lead_time_days,
        notes=notes.strip() or None,
    ))
    await db.commit()
    return RedirectResponse(url="/admin/suppliers/", status_code=302)


@router.post("/{supplier_id}/edit")
async def supplier_update(
    request: Request,
    supplier_id: str,
    name: str = Form(...),
    contact_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    website: str = Form(""),
    lead_time_days: int = Form(0),
    notes: str = Form(""),
    is_active: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    supplier.name = name.strip()
    supplier.contact_name = contact_name.strip() or None
    supplier.email = email.strip() or None
    supplier.phone = phone.strip() or None
    supplier.website = website.strip() or None
    supplier.lead_time_days = lead_time_days
    supplier.notes = notes.strip() or None
    supplier.is_active = is_active
    await db.commit()
    return RedirectResponse(url="/admin/suppliers/", status_code=302)


@router.post("/{supplier_id}/delete")
async def supplier_delete(
    request: Request,
    supplier_id: str,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    await db.delete(supplier)
    await db.commit()
    return RedirectResponse(url="/admin/suppliers/", status_code=302)
