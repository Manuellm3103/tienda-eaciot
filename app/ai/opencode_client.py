"""
OpenCode Go LLM client — second LLM provider alongside Ollama Cloud.
OpenCode Go excels at structured JSON, code generation, and SQL tasks.

Configure via .env:
    OPENCODE_HOST=http://localhost:8080
    OPENCODE_MODEL=opencode-go
"""

import httpx
from app.config import settings
from typing import Optional


class OpenCodeClient:
    """Thin client for the OpenCode Go LLM API (OpenAI-compatible endpoint)."""

    def __init__(self):
        self.host = getattr(settings, "opencode_host", "http://localhost:8080")
        self.model = getattr(settings, "opencode_model", "opencode-go")
        self.api_key = getattr(settings, "opencode_api_key", "")

    def _endpoint(self, path: str) -> str:
        """Build an OpenAI-compatible endpoint URL.

        Algunos proveedores dan la raíz de la API CON el prefijo /v1
        (p. ej. https://opencode.ai/zen/go/v1); otros dan solo el host.
        """
        base = self.host.rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        return f"{base}{path}"

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def generate(self, prompt: str, system: str = "", model: str = "") -> str:
        """Generate a completion via OpenAI-compatible /v1/chat/completions.

        The `system` message is passed as a chat role; the legacy
        /v1/completions endpoint does not accept a system field.

        Nota: max_tokens=2048 y timeout=180s son NECESARIOS para el paquete SEO
        del depto de marketing (JSON de ~180 palabras + bullets + términos).
        Con 1024 tokens / 60s el JSON se truncaba o daba ReadTimeout.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
            response = await client.post(
                self._endpoint("/chat/completions"),
                json={
                    "model": model or self.model,
                    "messages": messages,
                    "max_tokens": 2048,
                    "temperature": 0.7,
                },
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def list_models(self) -> list[str]:
        """Lista modelos vía /v1/models (OpenAI-compatible)."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            response = await client.get(self._endpoint("/models"), headers=self._headers())
            response.raise_for_status()
            data = response.json()
            return [
                m.get("id") or m.get("name") or ""
                for m in data.get("data", [])
            ]

    async def chat(self, messages: list[dict]) -> str:
        """Chat completion via OpenAI-compatible /v1/chat/completions."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=15.0)) as client:
            response = await client.post(
                self._endpoint("/chat/completions"),
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 2048,
                    "temperature": 0.7,
                },
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def health(self) -> bool:
        """Check if OpenCode Go is reachable.

        Tries `/v1/models` (OpenAI-compatible, widely supported) first and
        falls back to `/health` for servers that only expose a health route.
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self._endpoint("/models"))
                if resp.status_code == 200:
                    return True
                resp = await client.get(f"{self.host.rstrip('/')}/health")
                return resp.status_code == 200
        except Exception:
            return False


opencode_client = OpenCodeClient()
