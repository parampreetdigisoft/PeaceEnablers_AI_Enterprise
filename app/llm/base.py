"""LLM provider contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    usage: dict | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    @abstractmethod
    async def generate(
        self,
        *,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> LLMResult:
        ...
