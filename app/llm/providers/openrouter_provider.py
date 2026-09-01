from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.llm.base import LLMProvider, LLMResult


class OpenRouterProvider(LLMProvider):
    name = "openrouter"

    def is_configured(self) -> bool:
        return bool(settings.openrouter_api_key)

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
        prov = (routing.get("providers") or {}).get("openrouter") or {}
        model_name = model or prov.get("model") or "google/gemini-2.0-flash-exp:free"
        llm = ChatOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=model_name,
            temperature=temperature if temperature is not None else prov.get("temperature", 0.1),
            max_tokens=max_tokens or prov.get("max_tokens", 4000),
            default_headers={"HTTP-Referer": "http://localhost:8000", "X-Title": "PEM Aevum AI"},
        )
        msg = await llm.ainvoke(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        return LLMResult(text=str(msg.content), provider=self.name, model=model_name)
