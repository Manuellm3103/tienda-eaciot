import sys
import pytest
import app.services.search_service  # noqa: F401  (ensure the module is imported)
from app.models.product import Product, Category
from app.services.search_service import search_service

# `import app.services.search_service as x` binds the singleton, not the module
# (the package __init__ shadows the submodule), so resolve the real module here.
SEARCH_MODULE = sys.modules["app.services.search_service"]


class _StubRouter:
    def __init__(self):
        self.calls = 0

    async def generate_structured(self, prompt, system="", task_type=None):
        self.calls += 1
        return {"terms": ["auriculares", "headphones"]}


async def _make_product(db, title, slug="search-cat"):
    category = Category(name=title, slug=slug)
    db.add(category)
    await db.commit()
    await db.refresh(category)
    product = Product(
        title=title,
        description="demo",
        price=50,
        stock=5,
        category_id=category.id,
        product_type="fisico",
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


@pytest.mark.asyncio
async def test_search_expands_when_no_exact_match(db, monkeypatch):
    product = await _make_product(db, "Auriculares Inalámbricos", slug="audio")
    stub = _StubRouter()
    monkeypatch.setattr(SEARCH_MODULE, "llm_router", stub)

    result = await search_service.search_with_expansion(db, "headphones")
    assert result["ai_expanded"] is True
    assert "auriculares" in result["expanded_terms"]
    assert any(p.id == product.id for p in result["products"])


@pytest.mark.asyncio
async def test_search_skips_expansion_on_exact_match(db, monkeypatch):
    product = await _make_product(db, "Camiseta", slug="ropa")
    stub = _StubRouter()
    monkeypatch.setattr(SEARCH_MODULE, "llm_router", stub)

    result = await search_service.search_with_expansion(db, "Camiseta")
    assert result["ai_expanded"] is False
    assert stub.calls == 0
    assert any(p.id == product.id for p in result["products"])
