"""Choose which document collection a question should search.

Platform files live in the global collection.
A country file lives only in that country's collection.
A question about an event across countries searches every country collection
that actually has documents.
"""

from __future__ import annotations

from dataclasses import dataclass

_PLATFORM_HINTS = (
    "platform",
    "peace enabler",
    "peace mapper",
    "how do i",
    "how to",
    "where do i",
    "where can i",
    "where i found",
    "where is the",
    "what is this used for",
    "what is this platform",
    "what does this platform",
    "what is pem",
    "feature",
    "dashboard",
    "login",
    "sign in",
    "password",
    "upload document",
    "help centre",
    "help center",
    "navigation",
    "menu",
    "my account",
)

_CROSS_COUNTRY_HINTS = (
    "which countr",
    "in which countr",
    "across countr",
    "all countr",
    "every countr",
    "what countries",
    "which nations",
    "multiple countr",
    "between countr",
    "compare countr",
    "other countr",
)

_EVENT_HINTS = (
    "what is going on",
    "what's going on",
    "what is happening",
    "what's happening",
    "going on with",
    "happening with",
    "incident",
    "protest",
    "conflict",
    "crisis",
    "situation in",
)


@dataclass(frozen=True)
class RetrievalPlan:
    search_platform: bool = False
    search_country_id: int | None = None
    search_all_countries: bool = False
    reason: str = ""


def plan_retrieval(question: str, country_id: int | None = None) -> RetrievalPlan:
    text = (question or "").lower()
    platform = any(hint in text for hint in _PLATFORM_HINTS)
    cross = any(hint in text for hint in _CROSS_COUNTRY_HINTS)
    event = any(hint in text for hint in _EVENT_HINTS)

    if cross or (event and country_id is None):
        return RetrievalPlan(
            search_platform=platform,
            search_all_countries=True,
            reason="cross-country",
        )

    if platform and not event:
        return RetrievalPlan(search_platform=True, reason="platform")

    if country_id:
        return RetrievalPlan(
            search_platform=platform,
            search_country_id=country_id,
            reason="country",
        )

    return RetrievalPlan(search_platform=True, reason="platform-default")
