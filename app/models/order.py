import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey, JSON
from app.database import Base


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    shipping_amount = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    status = Column(String(20), default="pending")
    
    payment_method = Column(String(20))
    payment_id = Column(String(255))
    
    shipping_address = Column(JSON)
    tracking_number = Column(String(255))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price_at_purchase = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
