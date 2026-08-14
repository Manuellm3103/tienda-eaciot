"""RAG service using ChromaDB for product catalog semantic search.

Indexes active products into a local ChromaDB collection and retrieves
the most relevant products for a chat query.
"""
import os
import chromadb
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.product import Product


class RAGService:
    def __init__(self):
        self.persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="products",
            metadata={"hnsw:space": "cosine"},
        )

    async def index_products(self, db: AsyncSession) -> int:
        """Re-index all active products. Returns number of indexed documents."""
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
        if self.collection.count() == 0:
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
        return self.collection.count()


rag_service = RAGService()
