from io import StringIO
import csv
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.product import Product
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/reports",
    tags=["admin-reports"],
    dependencies=[Depends(require_admin)],
)


def _csv_response(filename: str, header: list[str], rows: list[list]) -> StreamingResponse:
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/", response_class=HTMLResponse)
async def reports_page(request: Request):
    return templates.TemplateResponse("admin/reports.html", {"request": request})


@router.get("/sales.csv")
async def sales_csv(db: AsyncSession = Depends(get_db)):
    """Export paid orders for accounting."""
    orders = (
        await db.execute(select(Order).order_by(Order.created_at.desc()))
    ).scalars().all()

    rows = []
    for o in orders:
        user = await db.get(User, o.user_id)
        item_count = (
            await db.execute(
                select(OrderItem).where(OrderItem.order_id == o.id)
            )
        ).scalars().all()
        rows.append(
            [
                o.id,
                o.created_at.isoformat() if o.created_at else "",
                (user.email if user else ""),
                o.status,
                o.payment_method or "",
                float(o.subtotal or 0),
                float(o.discount_amount or 0),
                float(o.shipping_amount or 0),
                float(o.total_amount or 0),
                len(item_count),
            ]
        )

    return _csv_response(
        "ventas.csv",
        [
            "order_id", "fecha", "email", "estado", "metodo_pago",
            "subtotal", "descuento", "envio", "total", "items",
        ],
        rows,
    )


@router.get("/products.csv")
async def products_csv(db: AsyncSession = Depends(get_db)):
    """Export product catalog + inventory."""
    products = (
        await db.execute(select(Product).order_by(Product.title))
    ).scalars().all()

    rows = [
        [
            p.id,
            p.title,
            p.product_type,
            float(p.price or 0),
            int(p.stock) if p.stock is not None else -1,
            "activo" if p.is_active else "inactivo",
            p.created_at.isoformat() if p.created_at else "",
        ]
        for p in products
    ]

    return _csv_response(
        "productos.csv",
        ["product_id", "titulo", "tipo", "precio", "stock", "estado", "fecha"],
        rows,
    )
