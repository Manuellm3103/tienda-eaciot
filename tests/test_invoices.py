import pytest
from sqlalchemy import select
from app.models.product import Product, Category
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.invoice import Invoice
from app.services.auth_service import create_access_token
from app.services.invoice_service import invoice_service


async def _paid_order(db, slug):
    category = Category(name="Inv Cat", slug=slug)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    product = Product(
        title="Invoiceable", description="demo", price=100, stock=5,
        category_id=category.id, product_type="fisico",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    user = User(email=f"{slug}@test.com", name="Buyer")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    order = Order(
        user_id=user.id, subtotal=100, total_amount=100, status="paid",
        customer_rfc="XAXX010101000", uso_cfdi="G03",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    db.add(OrderItem(order_id=order.id, product_id=product.id, quantity=1, price_at_purchase=100))
    await db.commit()
    return order


@pytest.mark.asyncio
async def test_get_or_create_invoice(db):
    order = await _paid_order(db, "inv-cat-1")
    inv = await invoice_service.get_or_create(db, order.id)
    assert inv is not None
    assert inv.order_id == order.id
    assert inv.customer_rfc == "XAXX010101000"
    # second call returns the same invoice
    inv2 = await invoice_service.get_or_create(db, order.id)
    assert inv2.id == inv.id


@pytest.mark.asyncio
async def test_issue_manual_fallback_without_key(db, monkeypatch):
    order = await _paid_order(db, "inv-cat-2")
    monkeypatch.setattr("app.services.invoice_service.settings.facturapi_api_key", "")
    inv = await invoice_service.issue(db, order.id)
    await db.commit()
    assert inv.status == "manual"
    assert inv.provider == "manual"
    assert "Comprobante de compra" in (inv.receipt_html or "")


@pytest.mark.asyncio
async def test_issue_rejects_unpaid_order(db):
    order = await _paid_order(db, "inv-cat-3")
    order.status = "pending"
    await db.commit()
    with pytest.raises(ValueError):
        await invoice_service.issue(db, order.id)


@pytest.mark.asyncio
async def test_satcfdi_degrades_gracefully_without_csd(db, monkeypatch):
    """When satcfdi is 'configured' but CSD files are missing, issue() must
    not crash — it marks the invoice failed and produces a fallback receipt."""
    import app.services.invoice_service as mod

    monkeypatch.setattr(mod.settings, "csd_cert_path", "/nonexistent.cer")
    monkeypatch.setattr(mod.settings, "csd_key_path", "/nonexistent.key")
    monkeypatch.setattr(mod.settings, "csd_password", "x")
    monkeypatch.setattr(mod.settings, "pac_username", "u")
    monkeypatch.setattr(mod.settings, "pac_password", "p")
    monkeypatch.setattr(mod.settings, "business_rfc", "EAC2403183F0")
    monkeypatch.setattr(mod.settings, "facturapi_api_key", "")

    order = await _paid_order(db, "inv-cat-4")
    inv = await invoice_service.issue(db, order.id)
    await db.commit()

    assert inv.status == "failed"
    assert inv.receipt_html  # printable fallback still produced


@pytest.mark.asyncio
async def test_admin_invoices_requires_admin(client):
    resp = await client.get("/admin/invoices/list")
    assert resp.status_code in (401, 403)
