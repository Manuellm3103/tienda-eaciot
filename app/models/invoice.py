import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from app.database import Base


class Invoice(Base):
    """Electronic invoice (CFDI) tied to a paid order.

    provider is 'satcfdi' (native CFDI 4.0 via a PAC), 'facturapi' (API), or
    'manual' (printable comprobante) when neither is configured.
    """

    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)

    customer_rfc = Column(String(20), nullable=True)
    customer_name = Column(String(255), nullable=True)
    uso_cfdi = Column(String(10), nullable=True, default="G03")

    status = Column(String(20), default="pending")  # pending, issued, failed, manual
    provider = Column(String(20), default="facturapi")
    provider_invoice_id = Column(String(255), nullable=True)  # UUID de la CFDI timbrada

    pdf_url = Column(String(500), nullable=True)
    xml_url = Column(String(500), nullable=True)
    xml_content = Column(Text, nullable=True)  # XML timbrado (satcfdi)
    receipt_html = Column(Text, nullable=True)  # fallback printable comprobante
    error = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
