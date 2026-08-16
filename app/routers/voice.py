"""Voice search router (#10 on the innovation roadmap)."""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.voice_service import voice_service

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/search")
async def voice_search(
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload audio, transcribe it, and return product results."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio data received")

    try:
        result = await voice_service.voice_search(audio_bytes, db)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Voice search unavailable: {exc}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {exc}",
        ) from exc

    return {
        "query": result["query"],
        "total": result["total"],
        "products": [
            {
                "id": str(p.id),
                "title": p.title,
                "price": float(p.price),
                "image_url": p.image_url,
                "description": (p.description or "")[:120],
            }
            for p in result["products"]
        ],
    }
