import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    image_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="category", lazy="selectin")


class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"))

    product_type = Column(String(20), nullable=False)  # ebook, curso, software, template, fisico

    image_url = Column(String)
    file_path = Column(String)
    weight = Column(Numeric(8, 2))

    # Enriched product content (specs + official videos) shown on the detail page.
    specs = Column(JSON, nullable=True)   # {"Procesador": "...", "RAM": "...", ...}
    videos = Column(JSON, nullable=True)  # ["https://...youtube...", ...]

    is_active = Column(Boolean, default=True)
    stock = Column(Integer, default=-1)

    meta_title = Column(String(255))
    meta_description = Column(Text)

    # AI-generated content metadata
    content_generated_at = Column(DateTime, nullable=True)
    content_score = Column(Numeric(5, 2), nullable=True)
    seo_score = Column(Numeric(5, 2), nullable=True)
    alt_texts = Column(JSON, nullable=True)  # list[str]

    # Dynamic pricing
    base_price = Column(Numeric(10, 2), nullable=True)
    dynamic_price = Column(Numeric(10, 2), nullable=True)
    dynamic_pricing_enabled = Column(Boolean, default=False)
    price_updated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("Category", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", lazy="selectin")
