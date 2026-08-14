import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, Boolean
from app.database import Base


class ProductVariant(Base):
    """A purchasable option of a product (size, color, edition, …).

    A variant carries its own price delta and stock, so the storefront can
    sell "Talla M" and "Talla L" of the same product with different stock
    and prices. price_delta is added to the base product price (may be ≤ 0).
    """

    __tablename__ = "product_variants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)  # e.g. "Talla M", "Color Rojo"
    sku = Column(String(255), unique=True, nullable=True, index=True)
    price_delta = Column(Numeric(10, 2), default=0.00)
    stock = Column(Integer, default=-1)  # -1 = unlimited
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
