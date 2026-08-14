from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.invoice_service import invoice_service
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/invoices",
    tags=["admin-invoices"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def invoices_page(request: Request):
    return templates.TemplateResponse("admin/invoices.html", {"request": request})


@router.get("/list")
async def list_invoices(db: AsyncSession = Depends(get_db)):
    return JSONResponse({"invoices": await invoice_service.list_invoices(db)})


@router.post("/{order_id}/issue")
async def issue_invoice(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await validate_csrf(request)
    try:
        invoice = await invoice_service.issue(db, order_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return JSONResponse(
        {
            "id": str(invoice.id),
            "status": invoice.status,
            "pdf_url": invoice.pdf_url,
            "xml_url": invoice.xml_url,
            "error": invoice.error,
        }
    )


@router.get("/{invoice_id}/receipt")
async def receipt_html(invoice_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.invoice import Invoice
    invoice = await db.get(Invoice, invoice_id)
    if not invoice or not invoice.receipt_html:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return Response(content=invoice.receipt_html, media_type="text/html")
