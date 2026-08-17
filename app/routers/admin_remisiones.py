"""Notas de remisión con logo — PDF por orden pagada.

Accesible desde el dashboard admin. Genera un PDF con el logo de Tienda
Eaciot, datos fiscales, cliente y detalle de artículos de la orden.
"""
import os
import tempfile
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from starlette.background import BackgroundTask
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/remisiones",
    tags=["admin-remisiones"],
    dependencies=[Depends(require_admin)],
)

LOGO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "app", "static", "images", "logo.png",
)


def _build_pdf(path: str, order: Order, user, items, product_titles: dict) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    from app.config import settings

    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.75 * 72, bottomMargin=0.75 * 72)
    styles = getSampleStyleSheet()
    story = []

    logo_ok = os.path.exists(LOGO)
    if logo_ok:
        try:
            img = Image(LOGO, width=110, height=110)
            img.hAlign = "CENTER"
            story.append(img)
        except Exception:
            pass

    title = Paragraph(
        f'<b>NOTA DE REMISIÓN</b><br/><font size="10">Folio: {str(order.id)[:8].upper()}</font>',
        styles["Title"],
    )
    story.append(title)
    story.append(Spacer(1, 10))

    empresa = (
        f'<b>{settings.business_name or "Tienda Eaciot"}</b><br/>'
        f'RFC: {settings.business_rfc or "—"} · Régimen: {settings.business_tax_regime or "—"}<br/>'
        f'CP: {settings.business_zip_code or "—"} · México'
    )
    fecha = datetime.utcnow().strftime("%d/%m/%Y %H:%M")

    addr = order.shipping_address or {}
    cliente = user.name or user.email if user else "Cliente"
    cliente_html = (
        f"<b>Cliente:</b> {cliente}<br/>"
        f"<b>Email:</b> {user.email if user else '—'}<br/>"
        f"<b>RFC:</b> {order.customer_rfc or '—'}<br/>"
        f"<b>Dirección:</b> {addr.get('calle', addr.get('address', '—'))} "
        f"{addr.get('ciudad', addr.get('city', ''))} {addr.get('cp', '')}"
    )

    info = Table(
        [
            [Paragraph(empresa, styles["Normal"]), Paragraph(cliente_html, styles["Normal"])],
            [Paragraph(f"<b>Fecha:</b> {fecha}", styles["Normal"]), Paragraph(f"<b>Orden:</b> {str(order.id)[:8]}", styles["Normal"])],
        ],
        colWidths=[270, 270],
    )
    info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info)
    story.append(Spacer(1, 14))

    rows = [["Cant.", "Descripción", "P. Unitario", "Importe"]]
    for it in items:
        titulo = product_titles.get(str(it.product_id), f"Producto {str(it.product_id)[:8]}")
        if it.variant_name:
            titulo = f"{titulo} ({it.variant_name})"
        rows.append([
            str(it.quantity),
            Paragraph(titulo[:80], styles["Normal"]),
            f"${float(it.price_at_purchase):,.2f}",
            f"${float(it.price_at_purchase) * it.quantity:,.2f}",
        ])
    rows.append(["", "", "TOTAL", f"${float(order.total_amount):,.2f}"])

    table = Table(rows, colWidths=[50, 320, 85, 85])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Documento que ampara la entrega de mercancía. No es factura fiscal.",
        styles["Italic"],
    ))

    doc.build(story)
    return path


@router.get("/", response_class=HTMLResponse)
async def remisiones_page(request: Request, db: AsyncSession = Depends(get_db)):
    orders = (
        await db.execute(
            select(Order).where(Order.status == "paid").order_by(Order.created_at.desc()).limit(50)
        )
    ).scalars().all()
    user_ids = [o.user_id for o in orders]
    users = {
        str(u.id): u
        for u in (
            await db.execute(select(User).where(User.id.in_(user_ids)))
        ).scalars().all()
    } if user_ids else {}
    return templates.TemplateResponse(
        "admin/remisiones.html",
        {"request": request, "orders": orders, "users": users},
    )


@router.get("/{order_id}/pdf")
async def remision_pdf(order_id: str, db: AsyncSession = Depends(get_db)):
    order = await db.get(Order, order_id)
    if not order or order.status != "paid":
        raise HTTPException(status_code=404, detail="Orden pagada no encontrada")

    user = await db.get(User, order.user_id)
    items = (
        await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    ).scalars().all()
    titles = {
        str(p.id): p.title
        for p in (
            await db.execute(
                select(Product).where(Product.id.in_([i.product_id for i in items]))
            )
        ).scalars().all()
    } if items else {}

    fd, path = tempfile.mkstemp(suffix=".pdf", prefix=f"remision_{order_id[:8]}_")
    os.close(fd)
    _build_pdf(path, order, user, items, titles)
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"remision_{str(order.id)[:8]}.pdf",
        background=BackgroundTask(os.remove, path),
    )
