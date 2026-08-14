import asyncio
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


@router.post("/{invoice_id}/cancel")
async def cancel_invoice(invoice_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Cancel a stamped CFDI through the PAC (Finkok cancel + get_sat_status)."""
    await validate_csrf(request)
    try:
        invoice = await invoice_service.cancel(db, invoice_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return JSONResponse(
        {"id": str(invoice.id), "status": invoice.status, "error": invoice.error}
    )


@router.get("/{invoice_id}/receipt")
async def receipt_html(invoice_id: str, db: AsyncSession = Depends(get_db)):
    from app.models.invoice import Invoice
    invoice = await db.get(Invoice, invoice_id)
    if not invoice or not invoice.receipt_html:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return Response(content=invoice.receipt_html, media_type="text/html")


@router.get("/{invoice_id}/xml")
async def invoice_xml(invoice_id: str, db: AsyncSession = Depends(get_db)):
    """Download the stamped CFDI XML."""
    from app.models.invoice import Invoice

    invoice = await db.get(Invoice, invoice_id)
    if not invoice or not invoice.xml_content:
        raise HTTPException(status_code=404, detail="XML not found")
    return Response(
        content=invoice.xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{invoice.provider_invoice_id or invoice_id}.xml"'},
    )


@router.get("/{invoice_id}/pdf")
async def invoice_pdf(invoice_id: str, db: AsyncSession = Depends(get_db)):
    """Render the invoice to a downloadable PDF (reportlab, pure Python)."""
    from app.models.invoice import Invoice
    from app.models.order import Order, OrderItem
    from app.models.product import Product
    from app.models.user import User
    from sqlalchemy import select

    invoice = await db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    order = await db.get(Order, invoice.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = (
        await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    ).scalars().all()
    item_rows = []
    for it in items:
        product = await db.get(Product, str(it.product_id))
        desc = (product.title if product else "Producto") + (
            f" · {it.variant_name}" if it.variant_name else ""
        )
        item_rows.append(
            {
                "description": desc[:120],
                "quantity": it.quantity,
                "price": float(it.price_at_purchase or 0),
            }
        )

    pdf_data = {
        "business_name": invoice.customer_name and None,  # placeholder, overwritten below
        "business_rfc": None,
        "customer_name": invoice.customer_name,
        "customer_rfc": invoice.customer_rfc,
        "uuid": invoice.provider_invoice_id,
        "order_id": str(order.id),
        "items": item_rows,
        "total": float(order.total_amount or 0),
        "created_at": order.created_at.strftime("%d/%m/%Y") if order.created_at else "",
    }
    # Correct emitter fields (business, not customer).
    from app.config import settings

    pdf_data["business_name"] = settings.business_name or "Tienda Eaciot"
    pdf_data["business_rfc"] = settings.business_rfc or ""

    def _render():
        from app.services.invoice_pdf import render_invoice_pdf

        return render_invoice_pdf(pdf_data)

    try:
        pdf = await asyncio.to_thread(_render)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"PDF no disponible: {str(exc)[:120]}")

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice.provider_invoice_id or invoice_id}.pdf"'
        },
    )
