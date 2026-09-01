from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.llm.base import LLMProvider, LLMResult


class LocalProvider(LLMProvider):
    """OpenAI-compatible local server (Ollama, vLLM). Used as degraded-mode fallback."""

    name = "local"

    def is_configured(self) -> bool:
        return bool(settings.local_llm_base_url)

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
        prov = (routing.get("providers") or {}).get("local") or {}
        model_name = model or prov.get("model") or settings.local_llm_model
        llm = ChatOpenAI(
            api_key="local",
            base_url=settings.local_llm_base_url,
            model=model_name,
            temperature=temperature if temperature is not None else prov.get("temperature", 0.1),
            max_tokens=max_tokens or prov.get("max_tokens", 2000),
        )
        msg = await llm.ainvoke(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        return LLMResult(text=str(msg.content), provider=self.name, model=model_name)
