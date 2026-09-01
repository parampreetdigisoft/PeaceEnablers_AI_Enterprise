"""
Neo4j client stub.

Phase 1 does not connect. Phase 2 (knowledge graph) will implement
session lifecycle, constraint bootstrap, and traversal helpers here.
No other package should import neo4j directly.
"""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class GraphStore:
    def healthy(self) -> dict[str, str]:
        return {
            "status": "not_connected",
            "phase": "2",
            "uri": settings.neo4j_uri,
            "note": "Graph queries are not enabled until Phase 2.",
        }


graph_store = GraphStore()
