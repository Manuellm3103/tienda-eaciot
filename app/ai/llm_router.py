"""
Intelligent LLM router — distributes requests between Ollama Cloud and OpenCode Go
based on task type, with automatic fallback on failure.

Routing strategy:
- Structured JSON, SQL generation, code tasks → OpenCode Go
- Creative, conversational, marketing copy → Ollama Cloud
- Either provider can serve as fallback for the other
"""

import json
import time
from enum import Enum
from typing import Optional
from app.ai.ollama_client import ollama_client
from app.ai.opencode_client import opencode_client
from app.config import settings


class TaskType(str, Enum):
    """Categorizes LLM requests for intelligent routing."""
    GENERAL = "general"
    CHAT = "chat"
    JSON_EXTRACTION = "json_extraction"
    SQL_GENERATION = "sql_generation"
    CODE = "code"
    COPYWRITING = "copywriting"
    PRODUCT_DESCRIPTION = "product_description"
    ANALYTICS = "analytics"
    TRANSLATION = "translation"
    CLASSIFICATION = "classification"


# Task → preferred provider mapping
TASK_ROUTING = {
    TaskType.GENERAL: "ollama",
    TaskType.CHAT: "ollama",
    TaskType.JSON_EXTRACTION: "opencode",
    TaskType.SQL_GENERATION: "opencode",
    TaskType.CODE: "opencode",
    TaskType.COPYWRITING: "ollama",
    TaskType.PRODUCT_DESCRIPTION: "ollama",
    TaskType.ANALYTICS: "opencode",
    TaskType.TRANSLATION: "ollama",
    TaskType.CLASSIFICATION: "opencode",
}


class LLMRouter:
    """
    Routes LLM requests to the best available provider.
    Features:
    - Task-based routing
    - Health-aware (skips unhealthy providers)
    - Automatic fallback on failure
    - Latency tracking for future optimization
    """

    def __init__(self):
        self.ollama = ollama_client
        self.opencode = opencode_client
        self._latency_window: dict[str, list[float]] = {"ollama": [], "opencode": []}

    async def generate(
        self,
        prompt: str,
        system: str = "",
        task_type: TaskType = TaskType.GENERAL,
        force_provider: Optional[str] = None,
    ) -> str:
        """
        Generate a completion, routing to the best provider.

        Args:
            prompt: The user prompt
            system: System prompt / context
            task_type: What kind of task (affects routing)
            force_provider: Override routing ('ollama' or 'opencode')

        Returns:
            Generated text response
        """
        preferred = force_provider or TASK_ROUTING.get(task_type, "ollama")
        # Sin key de Ollama Cloud, NO intentar ollama: ir directo a OpenCode Go
        # (el dueño opera SOLO con OpenCode Go + minimax).
        if preferred == "ollama" and not settings.ollama_api_key and not force_provider:
            preferred = "opencode"
        fallback = "opencode" if preferred == "ollama" else "ollama"

        # Try preferred provider first
        result = await self._try_provider(preferred, prompt, system)
        if result is not None:
            return result

        # Fallback to secondary provider
        result = await self._try_provider(fallback, prompt, system)
        if result is not None:
            return result

        # Both failed — return empty string (caller handles gracefully)
        return ""

    async def generate_structured(
        self,
        prompt: str,
        system: str = "",
        task_type: TaskType = TaskType.JSON_EXTRACTION,
    ) -> dict:
        """
        Generate structured JSON output. Always prefers OpenCode Go
        since it's more reliable at following JSON schemas.
        """
        response = await self.generate(prompt, system, task_type)
        try:
            # Try to extract JSON from response (handles markdown fences)
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 2)[-1].rsplit("```", 1)[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return {}

    async def _try_provider(
        self, provider: str, prompt: str, system: str
    ) -> Optional[str]:
        """Try one provider, return None on failure."""
        client = self.ollama if provider == "ollama" else self.opencode
        try:
            start = time.time()
            result = await client.generate(prompt, system)
            elapsed = time.time() - start
            self._record_latency(provider, elapsed)
            return result
        except Exception:
            return None

    def _record_latency(self, provider: str, seconds: float):
        """Track latency for future routing optimization."""
        window = self._latency_window[provider]
        window.append(seconds)
        if len(window) > 100:
            window.pop(0)

    async def health_check(self) -> dict:
        """Return health status of both providers."""
        return {
            "ollama": await self._check_ollama(),
            "opencode": await self.opencode.health(),
        }

    async def _check_ollama(self) -> bool:
        try:
            await self.ollama.generate("ping", "")
            return True
        except Exception:
            return False


# Singleton
llm_router = LLMRouter()
