import pytest
from io import BytesIO
from app.services.voice_service import voice_service


@pytest.mark.asyncio
async def test_voice_search_returns_products(client, db, monkeypatch):
    """Voice search transcribes audio and returns matching products."""
    from app.models.product import Category, Product
    from app.services.product_service import product_service
    from app.schemas.product import ProductCreate

    category = Category(name="Voz", slug="voz")
    db.add(category)
    await db.commit()
    await db.refresh(category)

    await product_service.create_product(
        db,
        ProductCreate(
            title="Auriculares Inalámbricos",
            description="Audio de alta calidad",
            price=899,
            category_id=category.id,
            product_type="fisico",
            stock=10,
        ),
    )
    await db.commit()

    async def fake_transcribe(_audio_bytes):
        return "auriculares"

    monkeypatch.setattr(voice_service, "transcribe", fake_transcribe)

    response = await client.post(
        "/api/voice/search",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "auriculares"
    assert data["total"] >= 1
    assert any("Auriculares" in p["title"] for p in data["products"])


@pytest.mark.asyncio
async def test_voice_search_missing_audio(client):
    response = await client.post("/api/voice/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_voice_search_unavailable_when_whisper_missing(client, monkeypatch):
    """If faster-whisper is missing, the endpoint returns 503."""

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("No module named faster_whisper")
        return original_import(name, *args, **kwargs)

    original_import = __builtins__["__import__"]
    monkeypatch.setitem(__builtins__, "__import__", fake_import)

    response = await client.post(
        "/api/voice/search",
        files={"audio": ("voice.webm", BytesIO(b"fake-audio"), "audio/webm")},
    )
    assert response.status_code == 503
    assert "Voice search unavailable" in response.json()["detail"]
