import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, JSON
from app.database import Base


class ShippingAddress(Base):
    __tablename__ = "shipping_addresses"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    phone = Column(String(50))
    street = Column(String(500), nullable=False)
    number = Column(String(50))
    apartment = Column(String(100))
    neighborhood = Column(String(255))
    city = Column(String(255), nullable=False)
    state = Column(String(255), nullable=False)
    zip_code = Column(String(20), nullable=False)
    country = Column(String(100), default="México")
    
    is_default = Column(String(1), default="0")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(String(36), primary_key=True, default=uuid.uuid4)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, index=True)
    
    carrier = Column(String(100))  # FedEx, DHL, Estafeta, etc.
    tracking_number = Column(String(255))
    tracking_url = Column(String(500))
    
    status = Column(String(50), default="pending")  # pending, picked_up, in_transit, delivered, returned
    estimated_delivery = Column(DateTime)
    delivered_at = Column(DateTime)
    
    weight = Column(Numeric(8, 2))
    dimensions = Column(JSON)  # {length, width, height}
    
    shipping_cost = Column(Numeric(10, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
