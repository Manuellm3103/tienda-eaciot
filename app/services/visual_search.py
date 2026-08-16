"""Visual Search (#4.4 on the innovation roadmap).

Uses a CLIP-style vision model to encode product images and query images into
embeddings, then returns the most visually similar products by cosine similarity.

The heavy `open_clip` / `torch` dependency is loaded lazily so the app starts
and runs normally when the dependency is not installed.
"""
from __future__ import annotations

import logging
import math
from io import BytesIO
from typing import Any

# numpy/PIL se importan de forma lazy (dentro de los métodos): igual que
# open_clip/torch, son dependencias opcionales y la app debe arrancar sin ellas.
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.product_embedding import ProductEmbedding

logger = logging.getLogger(__name__)

MODEL_NAME = "ViT-B-32"
MODEL_PRETRAINED = "laion2b_s34b_b79k"


class VisualSearchService:
    def __init__(self):
        self._model = None
        self._preprocess = None
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _load_model(self) -> tuple[Any, Any]:
        if self._model is not None:
            return self._model, self._preprocess
        try:
            import open_clip
            import torch

            model, _, preprocess = open_clip.create_model_and_transforms(
                MODEL_NAME, pretrained=MODEL_PRETRAINED
            )
            self._model = model
            self._preprocess = preprocess
            self._enabled = True
            return model, preprocess
        except Exception as exc:
            logger.warning("Visual search model unavailable: %s", exc)
            self._enabled = False
            raise RuntimeError("Visual search requiere open_clip/torch") from exc

    async def index_product(self, db: AsyncSession, product_id: str) -> bool:
        """Compute and store the embedding for a product's image."""
        product = await db.get(Product, product_id)
        if not product or not product.image_url:
            return False

        image_bytes = await self._fetch_image(product.image_url)
        if not image_bytes:
            return False

        embedding = await self._encode_image(image_bytes)
        if embedding is None:
            return False

        existing = (
            await db.execute(select(ProductEmbedding).where(ProductEmbedding.product_id == product_id))
        ).scalars().first()
        if existing:
            existing.embedding = embedding.tolist()
            existing.model_version = f"{MODEL_NAME}:{MODEL_PRETRAINED}"
        else:
            db.add(
                ProductEmbedding(
                    product_id=product_id,
                    embedding=embedding.tolist(),
                    model_version=f"{MODEL_NAME}:{MODEL_PRETRAINED}",
                )
            )
        await db.flush()
        return True

    async def index_all_products(self, db: AsyncSession) -> int:
        """Index all active products with an image_url."""
        result = await db.execute(select(Product).where(Product.is_active == True).where(Product.image_url.isnot(None)))
        products = result.scalars().all()
        count = 0
        for product in products:
            try:
                if await self.index_product(db, str(product.id)):
                    count += 1
            except Exception:
                logger.exception("Failed to index product %s", product.id)
        return count

    async def search(
        self, db: AsyncSession, query_image_bytes: bytes, top_k: int = 10
    ) -> list[dict[str, Any]]:
        """Return the top-k most visually similar products."""
        import numpy as np

        query_emb = await self._encode_image(query_image_bytes)
        if query_emb is None:
            return []

        result = await db.execute(select(ProductEmbedding))
        embeddings = result.scalars().all()
        if not embeddings:
            return []

        query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-9)
        scores: list[tuple[str, float]] = []
        for emb in embeddings:
            candidate = np.array(emb.embedding, dtype=np.float32)
            candidate_norm = candidate / (np.linalg.norm(candidate) + 1e-9)
            similarity = float(np.dot(query_norm, candidate_norm))
            scores.append((emb.product_id, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)
        top_ids = [product_id for product_id, _ in scores[:top_k]]

        products_result = await db.execute(select(Product).where(Product.id.in_(top_ids)))
        products = {str(p.id): p for p in products_result.scalars().all()}

        results = []
        for product_id, score in scores[:top_k]:
            product = products.get(product_id)
            if product:
                results.append(
                    {
                        "id": str(product.id),
                        "title": product.title,
                        "price": float(product.price),
                        "image_url": product.image_url,
                        "similarity": round(score, 4),
                    }
                )
        return results

    async def _encode_image(self, image_bytes: bytes) -> np.ndarray | None:
        try:
            self._load_model()
            import torch
            from PIL import Image

            image = Image.open(BytesIO(image_bytes)).convert("RGB")
            tensor = self._preprocess(image).unsqueeze(0)
            with torch.no_grad():
                embedding = self._model.encode_image(tensor)
            return embedding.numpy().flatten()
        except Exception as exc:
            logger.warning("Failed to encode image: %s", exc)
            return None

    async def _fetch_image(self, image_url: str) -> bytes | None:
        """Fetch image bytes from a URL or local path."""
        if image_url.startswith("http://") or image_url.startswith("https://"):
            try:
                import httpx

                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(image_url)
                    if resp.status_code == 200:
                        return resp.content
            except Exception as exc:
                logger.warning("Failed to fetch image %s: %s", image_url, exc)
            return None
        try:
            # Treat as local file path relative to static uploads
            path = image_url.lstrip("/")
            with open(path, "rb") as f:
                return f.read()
        except Exception as exc:
            logger.warning("Failed to read image %s: %s", image_url, exc)
            return None


visual_search_service = VisualSearchService()
