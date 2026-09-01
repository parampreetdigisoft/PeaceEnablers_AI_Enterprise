"""
Config-driven LLM router.

If a single provider is enabled (single_llm_mode: auto), every purpose uses that
provider. Combined with jobs/manager.py this means one LLM call per resource job
even when many users attach.

If multiple providers are enabled, purpose maps to a tier, then provider_order
+ fallback_order + circuit breaker pick the live model.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from app.core.config import settings
from app.core.exceptions import ProviderUnavailableError
from app.llm.base import LLMResult
from app.llm.cache import llm_cache
from app.llm.providers import PROVIDERS

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(self) -> None:
        self.failures: dict[str, int] = defaultdict(int)
        self.open_until: dict[str, float] = {}

    def allow(self, name: str) -> bool:
        until = self.open_until.get(name, 0)
        return time.time() >= until

    def success(self, name: str) -> None:
        self.failures[name] = 0
        self.open_until.pop(name, None)

    def fail(self, name: str, threshold: int, cooldown: float) -> None:
        self.failures[name] += 1
        if self.failures[name] >= threshold:
            self.open_until[name] = time.time() + cooldown
            logger.warning("Circuit open for provider %s for %ss", name, cooldown)


class LLMRouter:
    def __init__(self) -> None:
        self._breaker = CircuitBreaker()
        self._instances = {name: cls() for name, cls in PROVIDERS.items()}

    def _cfg(self) -> dict:
        return settings.llm_routing

    def enabled_providers(self) -> list[str]:
        providers = self._cfg().get("providers") or {}
        names = []
        for name, spec in providers.items():
            inst = self._instances.get(name)
            if spec.get("enabled") and inst and inst.is_configured():
                names.append(name)
        return names

    def _single_mode(self) -> str | None:
        mode = self._cfg().get("single_llm_mode", "auto")
        enabled = self.enabled_providers()
        if mode == "auto" and len(enabled) == 1:
            return enabled[0]
        return None

    def _tier_for_purpose(self, purpose: str) -> dict:
        tiers = self._cfg().get("tiers") or {}
        for spec in tiers.values():
            purposes = spec.get("purposes") or []
            if purpose == spec.get("purpose") or purpose in purposes:
                return spec
        return tiers.get("moderate") or {}

    def _candidate_names(self, purpose: str) -> list[str]:
        single = self._single_mode()
        if single:
            return [single]
        tier = self._tier_for_purpose(purpose)
        order = list(tier.get("provider_order") or [])
        for name in self._cfg().get("fallback_order") or []:
            if name not in order:
                order.append(name)
        enabled = set(self.enabled_providers())
        return [n for n in order if n in enabled]

    async def generate(
        self,
        *,
        purpose: str,
        system: str,
        user: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        job_id: str | None = None,
    ) -> LLMResult:
        cache_key = llm_cache.key(purpose, system, user)
        cached = llm_cache.get(cache_key)
        if cached:
            logger.info("LLM cache hit purpose=%s", purpose)
            return cached

        cb = self._cfg().get("circuit_breaker") or {}
        threshold = int(cb.get("failure_threshold", 3))
        cooldown = float(cb.get("cooldown_seconds", 60))
        last_error: Exception | None = None

        for name in self._candidate_names(purpose):
            if cb.get("enabled", True) and not self._breaker.allow(name):
                continue
            provider = self._instances[name]
            try:
                result = await provider.generate(
                    system=system,
                    user=user,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self._breaker.success(name)
                llm_cache.put(cache_key, result)
                if job_id:
                    from app.jobs.manager import job_manager

                    await job_manager.record_llm(job_id, result.provider, result.model)
                return result
            except Exception as exc:
                last_error = exc
                logger.warning("Provider %s failed for purpose=%s: %s", name, purpose, exc)
                if cb.get("enabled", True):
                    self._breaker.fail(name, threshold, cooldown)

        raise ProviderUnavailableError(
            f"All LLM providers failed for purpose={purpose}: {last_error}"
        )


llm_router = LLMRouter()
