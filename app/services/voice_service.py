"""Voice commerce service (#10 on the innovation roadmap).

Transcribes audio bytes to Spanish text using faster-whisper (optional) and
routes the resulting query through the existing search service.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.search_service import search_service


class VoiceCommerceService:
    """Speech-to-text product search."""

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Convert audio bytes to Spanish text using faster-whisper.

        Raises RuntimeError if faster-whisper is not installed or transcription
        fails. The caller is responsible for graceful fallback.
        """
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed") from exc

        import io
        import tempfile

        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            segments, _ = model.transcribe(tmp_path, language="es")
            return " ".join(segment.text for segment in segments).strip()
        finally:
            import os
            os.unlink(tmp_path)

    async def voice_search(
        self,
        audio_bytes: bytes,
        db: AsyncSession,
        per_page: int = 20,
    ) -> dict:
        """Transcribe audio and return matching products + the transcript."""
        query = await self.transcribe(audio_bytes)
        if not query:
            return {"query": "", "products": [], "total": 0}

        result = await search_service.search_products(
            db, query, per_page=per_page
        )
        return {
            "query": query,
            "products": result["products"],
            "total": result["total"],
        }


voice_service = VoiceCommerceService()
