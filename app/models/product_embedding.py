"""Vector embeddings for visual search.

Stores pre-computed image embeddings so visual similarity search can be done
without re-running the vision model at query time.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from app.database import Base


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, unique=True, index=True)
    embedding = Column(JSON, nullable=False)  # list[float]
    model_version = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
