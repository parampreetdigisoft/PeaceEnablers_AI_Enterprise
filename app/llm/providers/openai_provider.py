from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.llm.base import LLMProvider, LLMResult


class OpenAIProvider(LLMProvider):
    name = "openai"

    def is_configured(self) -> bool:
        return bool(settings.openai_api_key)

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
        prov = (routing.get("providers") or {}).get("openai") or {}
        llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=model or prov.get("model") or settings.openai_model,
            temperature=temperature if temperature is not None else prov.get("temperature", 0.1),
            max_tokens=max_tokens or prov.get("max_tokens", 4000),
        )
        msg = await llm.ainvoke(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        return LLMResult(
            text=str(msg.content),
            provider=self.name,
            model=model or prov.get("model") or settings.openai_model,
        )
