"""Resilient LLM gateway inspired by Agent-Span router patterns.

Features:
- Retry with exponential backoff.
- Simple circuit breaker: after N consecutive failures the backend is marked
  OPEN for a cooldown period and we return a fallback response.
- In-memory response cache with TTL for identical prompts.
"""
import asyncio
import hashlib
import httpx
import time
from typing import Any, Dict, Optional
from app.config import settings


class CircuitBreaker:
    """Simple fail-fast circuit breaker for the LLM backend."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"

    def can_attempt(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half_open"
                return True
            return False
        # half_open: allow one probe
        return True


class LLMGateway:
    def __init__(self):
        self.ollama_host = settings.ollama_host.rstrip("/")
        self.model = settings.ollama_model
        self.cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes

    def _cache_key(self, prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> Optional[str]:
        entry = self.cache.get(key)
        if entry and (time.time() - entry["ts"]) < self.cache_ttl:
            return entry["value"]
        if entry:
            del self.cache[key]
        return None

    def _set_cached(self, key: str, value: str) -> None:
        self.cache[key] = {"value": value, "ts": time.time()}

    async def generate(self, prompt: str, max_retries: int = 2) -> str:
        cache_key = self._cache_key(prompt)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        if not self.cb.can_attempt():
            return ""

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.ollama_host}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": 0.7},
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    answer = data.get("response", "").strip()
                    self.cb.record_success()
                    self._set_cached(cache_key, answer)
                    return answer
            except Exception as exc:
                last_error = exc
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)

        self.cb.record_failure()
        return ""


llm_gateway = LLMGateway()
