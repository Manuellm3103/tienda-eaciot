from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import require_admin
from app.middleware import validate_csrf
from app.services.shipping_service import shipping_service
from app.services.email_service import email_service
from app.templates_instance import templates

router = APIRouter(
    prefix="/admin/shipments",
    tags=["admin-shipments"],
    dependencies=[Depends(require_admin)],
)


@router.get("/", response_class=HTMLResponse)
async def shipments_page(request: Request):
    return templates.TemplateResponse("admin/shipments.html", {"request": request})


@router.get("/list")
async def shipments_list(db: AsyncSession = Depends(get_db)):
    rows = await shipping_service.list_shipments(db)
    return JSONResponse({"shipments": rows})


@router.post("/{shipment_id}/assign")
async def assign_tracking(
    request: Request,
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Assign carrier + tracking number to a shipment."""
    await validate_csrf(request)
    body = await request.json()
    carrier = (body.get("carrier") or "").strip()
    tracking_number = (body.get("tracking_number") or "").strip()
    if not carrier or not tracking_number:
        raise HTTPException(status_code=422, detail="carrier y tracking_number requeridos")

    shipment = await shipping_service.assign_tracking(
        db, shipment_id, carrier, tracking_number
    )
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    await db.commit()
    return JSONResponse(
        {"status": "assigned", "tracking_url": shipment.tracking_url}
    )


@router.post("/{shipment_id}/send-email")
async def send_shipping_email(
    request: Request,
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Send the 'enviado' email with tracking to the customer."""
    await validate_csrf(request)
    from app.models.shipping import Shipment
    from app.models.order import Order
    from app.models.user import User
    from sqlalchemy import select

    shipment = (
        await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    ).scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    order = await db.get(Order, shipment.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    user = await db.get(User, order.user_id)
    if not user or not user.email:
        raise HTTPException(status_code=422, detail="Cliente sin email")

    await email_service.send_shipping_confirmation_email(
        to_email=user.email,
        name=user.name or user.email,
        order_id=str(order.id),
        carrier=shipment.carrier or "",
        tracking_number=shipment.tracking_number or "",
        tracking_url=shipment.tracking_url,
    )
    return JSONResponse({"status": "sent", "to": user.email})
