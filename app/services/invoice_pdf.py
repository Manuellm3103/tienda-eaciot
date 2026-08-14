"""Invoice PDF generation with reportlab (pure Python, no system libraries).

WeasyPrint requires GTK/Pango system libs which are fragile on Windows and
Render. reportlab renders the comprobante directly, producing a clean, self-
contained PDF with the store logo.
"""
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

LOGO_PATH = os.path.join("app", "static", "images", "logo.png")


def render_invoice_pdf(data: dict) -> bytes:
    """data = {business_name, business_rfc, customer_name, customer_rfc,
    uuid, items:[{description,quantity,price}], total, created_at}"""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=20 * mm, bottomMargin=20 * mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleBig", parent=styles["Title"], fontSize=18)
    normal = styles["Normal"]
    small = ParagraphStyle("Small", parent=normal, fontSize=8, textColor=colors.grey)

    story = []

    # Logo + header
    if os.path.exists(LOGO_PATH):
        try:
            img = Image(LOGO_PATH, width=40 * mm, height=40 * mm)
            img.hAlign = "RIGHT"
            story.append(img)
        except Exception:
            pass

    story.append(Paragraph(f"<b>{data.get('business_name') or 'Tienda Eaciot'}</b>", title_style))
    story.append(Paragraph(f"RFC: {data.get('business_rfc') or '—'}", normal))
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("<b>Comprobante de compra</b>", styles["Heading2"]))
    story.append(Paragraph(
        f"Orden #{str(data.get('order_id', ''))[:8]} · {data.get('created_at') or ''}", normal
    ))
    story.append(Paragraph(
        f"Cliente: {data.get('customer_name') or '—'} · RFC: {data.get('customer_rfc') or '—'}",
        normal,
    ))
    if data.get("uuid"):
        story.append(Paragraph(f"<b>Folio fiscal (UUID):</b> {data['uuid']}", normal))
    story.append(Spacer(1, 6 * mm))

    # Items table
    rows = [["Producto", "Cant.", "Precio"]]
    for it in data.get("items", []):
        rows.append([it["description"], str(it["quantity"]), f"${float(it['price']):.2f}"])
    rows.append(["", "", ""])

    table = Table(rows, colWidths=[110 * mm, 20 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
                ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#dddddd")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        f"<font size=14><b>Total: ${float(data.get('total', 0)):.2f} MXN</b></font>", normal
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        "Este es un comprobante de venta. La factura CFDI (XML) está disponible en tu cuenta.",
        small,
    ))

    doc.build(story)
    return buf.getvalue()
