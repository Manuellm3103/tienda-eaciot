import pytest


@pytest.mark.asyncio
async def test_rag_degrades_gracefully_without_chromadb(db, monkeypatch):
    """When chromadb is absent (Render free tier), RAG must not crash."""
    import app.services.rag_service as module

    # Simulate chromadb not installed.
    monkeypatch.setattr(module, "chromadb", None)

    svc = module.RAGService()
    assert svc.available is False
    assert svc.size() == 0
    assert await svc.index_products(db) == 0
    assert await svc.retrieve("cualquier cosa") == []


@pytest.mark.asyncio
async def test_rag_handles_client_failure(db, monkeypatch):
    """If chromadb is installed but fails to initialize, degrade too."""
    import app.services.rag_service as module

    class BrokenChromadb:
        @staticmethod
        def PersistentClient(path):
            raise RuntimeError("no disk")

    monkeypatch.setattr(module, "chromadb", BrokenChromadb)
    svc = module.RAGService()
    assert svc.available is False
    assert svc.size() == 0
