from __future__ import annotations

import httpx

from app.core.config import settings
from app.llm.base import LLMProvider, LLMResult


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    async def generate(
        self,
        *,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> LLMResult:
        routing = settings.llm_routing
        prov = (routing.get("providers") or {}).get("anthropic") or {}
        model_name = model or prov.get("model") or "claude-3-5-haiku-latest"
        tokens = max_tokens or prov.get("max_tokens") or 4000
        temp = temperature if temperature is not None else prov.get("temperature", 0.1)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model_name,
                    "max_tokens": tokens,
                    "temperature": temp,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
            )
            response.raise_for_status()
            data = response.json()
        text = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        return LLMResult(text=text, provider=self.name, model=model_name)
