"""Exact-match semantic cache (in-process). Phase 5 can swap Redis without changing callers."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from app.core.config import settings
from app.llm.base import LLMResult


@dataclass
class _Entry:
    result: LLMResult
    expires_at: float


class LLMCache:
    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}

    def _enabled(self) -> bool:
        return bool((settings.llm_routing.get("semantic_cache") or {}).get("enabled", False))

    def _ttl(self) -> int:
        return int((settings.llm_routing.get("semantic_cache") or {}).get("ttl_seconds", 3600))

    @staticmethod
    def key(purpose: str, system: str, user: str) -> str:
        blob = f"{purpose}\n{system}\n{user}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> LLMResult | None:
        if not self._enabled():
            return None
        entry = self._store.get(cache_key)
        if not entry:
            return None
        if entry.expires_at < time.time():
            self._store.pop(cache_key, None)
            return None
        return entry.result

    def put(self, cache_key: str, result: LLMResult) -> None:
        if not self._enabled():
            return
        self._store[cache_key] = _Entry(result=result, expires_at=time.time() + self._ttl())


llm_cache = LLMCache()
