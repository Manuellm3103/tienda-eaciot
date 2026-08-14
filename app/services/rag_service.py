"""RAG service using ChromaDB for product catalog semantic search.

Chromadb is an OPTIONAL dependency: on Render's free tier the filesystem is
ephemeral and chromadb is heavy, so it may not be installed. This module
degrades gracefully — when chromadb is missing, `available` is False and
`retrieve` returns an empty list, so the product advisor falls back to
keyword search. Install it locally with `pip install chromadb` to enable RAG.
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product

try:
    import chromadb
except Exception:  # pragma: no cover - optional dependency
    chromadb = None


class RAGService:
    def __init__(self):
        self.available = chromadb is not None
        self.client = None
        self.collection = None
        if self.available:
            self.persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
            try:
                self.client = chromadb.PersistentClient(path=self.persist_directory)
                self.collection = self.client.get_or_create_collection(
                    name="products",
                    metadata={"hnsw:space": "cosine"},
                )
            except Exception:
                self.available = False
                self.client = None
                self.collection = None

    async def index_products(self, db: AsyncSession) -> int:
        """Re-index all active products. Returns number of indexed documents."""
        if not self.available:
            return 0

        result = await db.execute(select(Product).where(Product.is_active == True))
        products = result.scalars().all()

        ids = []
        documents = []
        metadatas = []

        for p in products:
            ids.append(str(p.id))
            documents.append(f"{p.title}\n{p.description or ''}")
            metadatas.append(
                {
                    "id": str(p.id),
                    "title": p.title,
                    "price": float(p.price),
                    "image_url": p.image_url or "",
                }
            )

        if ids:
            self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        return len(ids)

    async def retrieve(self, query: str, n: int = 5) -> list[dict]:
        """Retrieve top-n products relevant to the query."""
        if not self.available or self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(n, self.collection.count()),
            include=["metadatas", "documents", "distances"],
        )

        products = []
        if results and results.get("metadatas"):
            for i, meta in enumerate(results["metadatas"][0]):
                products.append(
                    {
                        "id": meta.get("id"),
                        "title": meta.get("title"),
                        "price": meta.get("price"),
                        "image_url": meta.get("image_url"),
                        "relevance_score": 1 - (results["distances"][0][i] or 0),
                    }
                )
        return products

    def size(self) -> int:
        """Number of documents currently indexed in the vector store."""
        if not self.available:
            return 0
        return self.collection.count()


rag_service = RAGService()
