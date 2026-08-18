import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Supplier(Base):
    """Proveedor de producto.

    Permite al admin registrar quién surte cada producto (HP, distribuidores de
    componentes, etc.) con datos de contacto, tiempo de entrega y notas. Un
    producto puede asociarse a un proveedor para saber a quién re-ordenar.
    """

    __tablename__ = "suppliers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    contact_name = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))
    lead_time_days = Column(Integer, default=0)  # días típicos para surtir
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    products = relationship("Product", back_populates="supplier")
