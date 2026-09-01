"""
Web / open-source fallback when SQL and vector both miss.

Phase 1: returns empty unless WEB_SEARCH is later wired. Phase 3 ingestion
and the enterprise PDF web-search policy belong here, not in services.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class WebFallback:
    async def search(self, question: str) -> str:
        logger.info("Web fallback not configured; skipping for: %s", question[:80])
        return ""


web_fallback = WebFallback()
