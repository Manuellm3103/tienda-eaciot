import httpx
from app.config import settings


class OllamaClient:
    def __init__(self):
        self.host = settings.ollama_host
        self.model = settings.ollama_model
    
    async def generate(self, prompt: str, system: str = "") -> str:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            response = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]
    
    async def chat(self, messages: list) -> str:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            response = await client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["message"]["content"]


ollama_client = OllamaClient()
