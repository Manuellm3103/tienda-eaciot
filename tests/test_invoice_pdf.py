from app.services.invoice_pdf import render_invoice_pdf


def test_render_invoice_pdf_produces_pdf_bytes():
    data = {
        "business_name": "EMANUEL AZUR CORPORATIVO SAS",
        "business_rfc": "EAC2403183F0",
        "customer_name": "Cliente",
        "customer_rfc": "XAXX010101000",
        "uuid": "11111111-2222-3333-4444-555555555555",
        "order_id": "abc12345",
        "items": [
            {"description": "Producto A", "quantity": 2, "price": 50.0},
        ],
        "total": 100.0,
        "created_at": "14/08/2026",
    }
    pdf = render_invoice_pdf(data)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000
