"""CFDI electronic invoicing (#12).

Provider precedence:
1. satcfdi + PAC (native CFDI 4.0, no monthly limits) — when CSD + PAC creds
   are configured.
2. Facturapi API — when FACTURAPI_API_KEY is set (capped on free tier).
3. Manual printable comprobante — always available as a graceful fallback, so
   the store never breaks because of missing invoicing.
"""
import base64
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.models.invoice import Invoice
from app.models.order import Order, OrderItem
from app.models.user import User

LOGO_PATH = os.path.join("app", "static", "images", "logo.png")


class InvoiceService:
    @property
    def satcfdi_configured(self) -> bool:
        return bool(
            settings.csd_cert_path
            and settings.csd_key_path
            and settings.pac_username
            and settings.pac_password
            and settings.business_rfc
        )

    @property
    def facturapi_configured(self) -> bool:
        return bool(settings.facturapi_api_key and settings.business_rfc)

    @property
    def configured(self) -> bool:
        return self.satcfdi_configured or self.facturapi_configured

    async def get_or_create(self, db: AsyncSession, order_id: str) -> Optional[Invoice]:
        result = await db.execute(select(Invoice).where(Invoice.order_id == order_id))
        invoice = result.scalar_one_or_none()
        if invoice:
            return invoice

        order = await db.get(Order, order_id)
        if not order:
            return None

        user = await db.get(User, order.user_id)
        provider = "satcfdi" if self.satcfdi_configured else (
            "facturapi" if self.facturapi_configured else "manual"
        )
        invoice = Invoice(
            order_id=order_id,
            customer_rfc=order.customer_rfc,
            customer_name=(user.name or user.email) if user else None,
            uso_cfdi=order.uso_cfdi or "G03",
            status="pending",
            provider=provider,
        )
        db.add(invoice)
        await db.flush()
        return invoice

    async def issue(self, db: AsyncSession, order_id: str) -> Invoice:
        """Issue (or regenerate) the invoice for a paid order."""
        invoice = await self.get_or_create(db, order_id)
        if invoice is None:
            raise ValueError("Order not found")

        order = await db.get(Order, order_id)
        if order.status != "paid":
            raise ValueError("Solo órdenes pagadas pueden facturarse")

        if self.satcfdi_configured:
            return await self._issue_satcfdi(db, invoice, order)
        if self.facturapi_configured:
            return await self._issue_facturapi(db, invoice, order)
        return await self._issue_manual(db, invoice, order)

    async def cancel(self, db: AsyncSession, invoice_id: str) -> Invoice:
        """Cancel a stamped CFDI via the PAC (Finkok).

        Embeds the CSD for immediate cancellation when configured; otherwise
        queues a pending cancellation (store_pending) for portal confirmation.
        """
        invoice = await db.get(Invoice, invoice_id)
        if not invoice:
            raise ValueError("Invoice not found")
        if invoice.status != "issued" or invoice.provider != "satcfdi":
            raise ValueError("Solo facturas timbradas (satcfdi) pueden cancelarse")
        if not invoice.provider_invoice_id:
            raise ValueError("La factura no tiene UUID de timbrado")
        if not settings.business_rfc:
            raise ValueError("Falta BUSINESS_RFC para cancelar")

        import asyncio

        def _run():
            from app.services.cfdi_finkok import finkok_client

            cer_b64 = key_b64 = None
            if settings.csd_cert_path and settings.csd_key_path and settings.csd_password:
                cer_b64 = base64.b64encode(open(settings.csd_cert_path, "rb").read()).decode("ascii")
                key_b64 = base64.b64encode(open(settings.csd_key_path, "rb").read()).decode("ascii")
            return finkok_client.cancel(
                uuid=invoice.provider_invoice_id,
                taxpayer_id=settings.business_rfc,
                cer_b64=cer_b64,
                key_b64=key_b64,
                store_pending=not (cer_b64 and key_b64),
            )

        try:
            result = await asyncio.to_thread(_run)
        except Exception as exc:
            invoice.error = f"Cancelación fallida: {str(exc)[:400]}"
            await db.flush()
            return invoice

        # 202 = cancelado; 201 = pendiente de cancelación (portal).
        invoice.status = "cancelled" if result.get("estatus") == "202" else "cancel_pending"
        invoice.error = None
        await db.flush()
        return invoice

    async def _issue_satcfdi(self, db, invoice: Invoice, order: Order) -> Invoice:
        """Generate + sign + stamp a CFDI 4.0 via satcfdi + PAC."""
        import asyncio

        items = await self._order_items(db, order)

        def _run():
            from app.services.cfdi_satcfdi import SATCFDIIssuer

            issuer = SATCFDIIssuer()
            return issuer.issue(
                customer_rfc=invoice.customer_rfc or "XAXX010101000",
                customer_name=invoice.customer_name or "PUBLICO EN GENERAL",
                uso_cfdi=invoice.uso_cfdi or "G03",
                items=items,
                shipping_amount=order.shipping_amount or Decimal("0"),
                payment_method=order.payment_method or "stripe",
            )

        try:
            result = await asyncio.to_thread(_run)
        except Exception as exc:
            invoice.status = "failed"
            invoice.error = str(exc)[:500]
            # still produce a printable fallback receipt for the customer
            invoice.receipt_html = await self._render_receipt(db, invoice, order)
            await db.flush()
            return invoice

        invoice.status = "issued"
        invoice.provider = "satcfdi"
        invoice.provider_invoice_id = result.get("uuid")
        invoice.xml_content = result.get("xml")
        invoice.receipt_html = await self._render_receipt(db, invoice, order)
        await db.flush()
        return invoice

    async def _issue_facturapi(self, db, invoice: Invoice, order: Order) -> Invoice:
        payload = await self._build_cfdi_payload(db, order)
        headers = {
            "Authorization": f"Bearer {settings.facturapi_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{settings.facturapi_base_url}/invoices",
                    json=payload,
                    headers=headers,
                )
                if resp.status_code >= 400:
                    invoice.status = "failed"
                    invoice.error = (resp.text or "Facturapi error")[:500]
                    await db.flush()
                    return invoice
                data = resp.json()
        except Exception as exc:
            invoice.status = "failed"
            invoice.error = str(exc)[:500]
            await db.flush()
            return invoice

        invoice.status = "issued"
        invoice.provider = "facturapi"
        invoice.provider_invoice_id = data.get("id")
        invoice.pdf_url = data.get("pdf_url") or (data.get("verification_url"))
        invoice.xml_url = data.get("xml_url")
        await db.flush()
        return invoice

    async def _issue_manual(self, db, invoice: Invoice, order: Order) -> Invoice:
        invoice.status = "manual"
        invoice.provider = "manual"
        invoice.receipt_html = await self._render_receipt(db, invoice, order)
        await db.flush()
        return invoice

    async def _order_items(self, db: AsyncSession, order: Order) -> list[dict]:
        """Line items in satcfdi's expected shape: description/quantity/unit_price."""
        rows = (
            await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
        ).scalars().all()
        from app.models.product import Product

        items = []
        for it in rows:
            product = await db.get(Product, str(it.product_id))
            desc = (product.title if product else "Producto") + (
                f" · {it.variant_name}" if it.variant_name else ""
            )
            items.append(
                {
                    "description": desc[:300],
                    "quantity": it.quantity,
                    "unit_price": float(it.price_at_purchase or 0),
                }
            )
        return items

    @staticmethod
    def _logo_data_uri() -> str:
        """Embed the store logo as a base64 data URI for self-contained receipts."""
        try:
            if os.path.exists(LOGO_PATH):
                with open(LOGO_PATH, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                return f'<img src="data:image/png;base64,{b64}" alt="Logo" style="height:60px;">'
        except Exception:
            pass
        return ""

    async def _build_cfdi_payload(self, db: AsyncSession, order: Order) -> dict:
        items = (
            await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
        ).scalars().all()
        from app.models.product import Product

        item_payloads = []
        for it in items:
            product = await db.get(Product, str(it.product_id))
            desc = (product.title if product else "Producto") + (
                f" · {it.variant_name}" if it.variant_name else ""
            )
            item_payloads.append(
                {
                    "quantity": it.quantity,
                    "product": {
                        "description": desc[:300],
                        "product_key": "60131300",  # servicios digitales/otros
                        "price": float(it.price_at_purchase or 0),
                    },
                }
            )

        return {
            "customer": {
                "legal_name": (invoice.customer_name or "Consumidor")[:200],
                "tax_id": (invoice.customer_rfc or "XAXX010101000"),
                "email": None,
                "address": {"zip": "62000"},
            },
            "items": item_payloads,
            "payment_form": "03",  # transferencia / tarjeta
            "use": invoice.uso_cfdi or "G03",
        }

    async def _render_receipt(self, db, invoice: Invoice, order: Order) -> str:
        """Printable HTML comprobante (fallback sin API key)."""
        items = (
            await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
        ).scalars().all()
        from app.models.product import Product

        rows = []
        for it in items:
            product = await db.get(Product, str(it.product_id))
            title = (product.title if product else "Producto") + (
                f" · {it.variant_name}" if it.variant_name else ""
            )
            rows.append(
                f"<tr><td>{title}</td><td>{it.quantity}</td>"
                f"<td>${float(it.price_at_purchase or 0):.2f}</td></tr>"
            )

        logo = self._logo_data_uri()
        footer_note = (
            "Este es un comprobante provisional. La factura CFDI se emitirá al configurar el proveedor de facturación."
            if invoice.provider == "manual"
            else "Comprobante de venta — la CFDI (XML) está disponible en tu cuenta."
        )
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:Arial,sans-serif;color:#333;}} .c{{max-width:640px;margin:0 auto;padding:20px;}}
h1{{font-size:22px;}} table{{width:100%;border-collapse:collapse;margin:20px 0;}}
td,th{{border:1px solid #ddd;padding:8px;text-align:left;}} th{{background:#f5f5f5;}}
.tot{{font-size:20px;font-weight:bold;}}</style></head><body><div class="c">
{logo}
<h1>Comprobante de compra</h1>
<p><strong>{settings.business_name or 'Tienda Eaciot'}</strong> · RFC: {settings.business_rfc or '—'}</p>
<p>Orden #{str(order.id)[:8]} · {order.created_at.strftime('%d/%m/%Y') if order.created_at else ''}</p>
<p>Cliente: {invoice.customer_name or '—'} · RFC: {invoice.customer_rfc or '—'}</p>
<table><tr><th>Producto</th><th>Cant.</th><th>Precio</th></tr>{''.join(rows)}</table>
<p class="tot">Total: ${float(order.total_amount or 0):.2f} MXN</p>
<p style="color:#888;font-size:12px;">{footer_note}</p>
</div></body></html>"""

    async def list_invoices(self, db: AsyncSession, limit: int = 100) -> list[dict]:
        invoices = (
            await db.execute(select(Invoice).order_by(Invoice.created_at.desc()).limit(limit))
        ).scalars().all()
        rows = []
        for inv in invoices:
            order = await db.get(Order, inv.order_id)
            rows.append(
                {
                    "id": str(inv.id),
                    "order_id": str(inv.order_id),
                    "customer_name": inv.customer_name,
                    "customer_rfc": inv.customer_rfc,
                    "status": inv.status,
                    "provider": inv.provider,
                    "pdf_url": inv.pdf_url,
                    "xml_url": inv.xml_url,
                    "has_xml": bool(inv.xml_content),
                    "error": inv.error,
                    "total": float(order.total_amount or 0) if order else 0.0,
                    "created_at": inv.created_at.isoformat() if inv.created_at else "",
                }
            )
        return rows


invoice_service = InvoiceService()
