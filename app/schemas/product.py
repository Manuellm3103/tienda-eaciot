from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal
from uuid import UUID
from datetime import datetime


class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    image_url: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryResponse(CategoryBase):
    id: UUID
    is_active: bool
    
    class Config:
        from_attributes = True


class ProductBase(BaseModel):
    title: str
    description: Optional[str] = None
    price: Decimal = Field(gt=0)
    category_id: Optional[UUID] = None
    product_type: str = Field(pattern="^(ebook|curso|software|template|fisico)$")
    image_url: Optional[str] = None
    stock: int = -1
    specs: Optional[dict] = None
    videos: Optional[list[str]] = None
    # Precio de competencia (anclaje) — se muestra tachado con % de ahorro.
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    # Precios internos (SOLO admin, nunca en la tienda pública).
    cost_price: Optional[Decimal] = Field(None, gt=0)
    hp_price: Optional[Decimal] = Field(None, gt=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    category_id: Optional[UUID] = None
    product_type: Optional[str] = None
    image_url: Optional[str] = None
    stock: Optional[int] = None
    specs: Optional[dict] = None
    videos: Optional[list[str]] = None
    is_active: Optional[bool] = None
    compare_at_price: Optional[Decimal] = Field(None, gt=0)
    cost_price: Optional[Decimal] = Field(None, gt=0)
    hp_price: Optional[Decimal] = Field(None, gt=0)


class ProductResponse(ProductBase):
    id: UUID
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
