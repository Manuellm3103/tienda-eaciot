"""AI Semantic Search + Faceted Navigation (#2.1 on the innovation roadmap).

Wraps Meilisearch when available and falls back to the existing SQL search
service so the storefront keeps working even if the Meilisearch container is
down. Products are indexed with title, description, category, price and
search_terms so typo-tolerant and faceted queries work out of the box.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Optional Meilisearch-backed semantic search with SQL fallback."""

    def __init__(self) -> None:
        self._client: Any | None = None
        self._index_name = "products"
        try:
            from app.config import settings

            self._url = getattr(settings, "meilisearch_url", "http://localhost:7700")
            self._key = getattr(settings, "meilisearch_api_key", "")
            enabled = getattr(settings, "semantic_search_enabled", False)
            if enabled and self._url:
                import meilisearch

                self._client = meilisearch.Client(self._url, self._key or None)
        except Exception as exc:  # pragma: no cover
            logger.warning("Meilisearch client unavailable: %s", exc)
            self._client = None

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def ensure_index(self) -> bool:
        """Create the index and configure filterable attributes."""
        if not self._client:
            return False
        try:
            indexes = self._client.get_indexes()
            existing = {idx.uid for idx in indexes.get("results", [])}
            if self._index_name not in existing:
                self._client.create_index(self._index_name, {"primaryKey": "id"})
            self._client.index(self._index_name).update_filterable_attributes(
                ["category", "product_type", "price"]
            )
            self._client.index(self._index_name).update_searchable_attributes(
                ["title", "description", "search_terms", "category"]
            )
            return True
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to configure Meilisearch index: %s", exc)
            return False

    async def index_products(self, db: AsyncSession) -> int:
        """Sync all active products to Meilisearch."""
        if not self._client:
            return 0
        await self.ensure_index()
        products = (
            await db.execute(
                select(Product)
                .where(Product.is_active == True)
                .options(selectinload(Product.category))
            )
        ).scalars().all()

        documents: list[dict[str, Any]] = []
        for p in products:
            documents.append(
                {
                    "id": str(p.id),
                    "title": p.title,
                    "description": p.description or "",
                    "category": p.category.name if p.category else "",
                    "category_id": str(p.category_id) if p.category_id else "",
                    "price": float(p.price) if p.price is not None else 0.0,
                    "product_type": p.product_type or "",
                    "search_terms": getattr(p, "search_terms", None) or "",
                    "image_url": getattr(p, "image_url", None) or "",
                }
            )

        if documents:
            try:
                self._client.index(self._index_name).add_documents(documents)
            except Exception as exc:  # pragma: no cover
                logger.warning("Meilisearch indexing failed: %s", exc)
                return 0
        return len(documents)

    async def search(
        self,
        db: AsyncSession,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search with Meilisearch or fall back to SQL search."""
        if self._client:
            try:
                return await self._meilisearch_search(query, filters, limit)
            except Exception as exc:  # pragma: no cover
                logger.warning("Meilisearch search failed, falling back: %s", exc)
        return await self._sql_fallback(db, query, filters, limit)

    async def _meilisearch_search(
        self, query: str, filters: dict[str, Any] | None, limit: int
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "limit": limit,
            "attributesToHighlight": ["title", "description"],
            "attributesToCrop": ["description"],
            "cropLength": 150,
        }
        filter_parts = self._build_filter(filters)
        if filter_parts:
            params["filter"] = filter_parts

        result = self._client.index(self._index_name).search(query, params)
        hits = result.get("hits", [])
        ids = [h["id"] for h in hits]
        return {
            "source": "meilisearch",
            "total": result.get("estimatedTotalHits", len(hits)),
            "product_ids": ids,
            "hits": hits,
        }

    async def _sql_fallback(
        self,
        db: AsyncSession,
        query: str,
        filters: dict[str, Any] | None,
        limit: int,
    ) -> dict[str, Any]:
        filters = filters or {}
        category_id = filters.get("category_id")
        min_price = filters.get("min_price")
        max_price = filters.get("max_price")
        product_type = filters.get("product_type")

        result = await search_service.search_products(
            db,
            query,
            category_id=category_id,
            min_price=min_price,
            max_price=max_price,
            product_type=product_type,
            per_page=limit,
        )
        return {
            "source": "sql",
            "total": result["total"],
            "product_ids": [str(p.id) for p in result["products"]],
            "products": result["products"],
        }

    def _build_filter(self, filters: dict[str, Any] | None) -> list[str] | None:
        if not filters:
            return None
        parts: list[str] = []
        if filters.get("category"):
            parts.append(f"category = '{filters['category']}'")
        if filters.get("product_type"):
            parts.append(f"product_type = '{filters['product_type']}'")
        if filters.get("min_price") is not None:
            parts.append(f"price >= {filters['min_price']}")
        if filters.get("max_price") is not None:
            parts.append(f"price <= {filters['max_price']}")
        return parts if parts else None

    async def get_facet_values(self, db: AsyncSession) -> dict[str, list[Any]]:
        """Return facet options from SQL (used when Meilisearch is off)."""
        from app.models.product import Category

        categories = (
            await db.execute(select(Category.name).where(Category.is_active == True))
        ).scalars().all()
        return {
            "categories": sorted(set(categories)),
            "product_types": ["fisico", "digital"],
        }


semantic_search_service = SemanticSearchService()
