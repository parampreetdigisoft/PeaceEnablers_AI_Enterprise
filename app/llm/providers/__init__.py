from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.anthropic_provider import AnthropicProvider
from app.llm.providers.local_provider import LocalProvider
from app.llm.providers.openrouter_provider import OpenRouterProvider

PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "local": LocalProvider,
    "openrouter": OpenRouterProvider,
}
