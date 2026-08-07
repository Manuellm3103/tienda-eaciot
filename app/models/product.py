import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Numeric, DateTime, Text, ForeignKey
from app.database import Base


class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    image_url = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"))
    
    product_type = Column(String(20), nullable=False)  # ebook, curso, software, template, fisico
    
    image_url = Column(String)
    file_path = Column(String)
    weight = Column(Numeric(8, 2))
    
    is_active = Column(Boolean, default=True)
    stock = Column(Integer, default=-1)
    
    meta_title = Column(String(255))
    meta_description = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
