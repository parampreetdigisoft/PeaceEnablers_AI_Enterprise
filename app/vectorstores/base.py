"""Vector-store interface. No backend-specific imports belong here."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings


class VectorStore(ABC):
    """Backend-agnostic vector operations used by RAG ingest and retrieval."""

    def collection_name(
        self,
        *,
        country_id: int | None = None,
        global_docs: bool = False,
    ) -> str:
        """Logical collection/index name. Backends may map this to namespaces."""
        prefix = settings.vector_collection_prefix
        if global_docs:
            return f"{prefix}_global"
        if country_id is None:
            return f"{prefix}_default"
        return f"{prefix}_country_{country_id}"

    @abstractmethod
    def query(
        self,
        name: str,
        embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[str]:
        """Return nearest document texts for an embedding."""

    @abstractmethod
    def upsert(
        self,
        name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        """Insert or replace vectors. Each row is id + embedding + document + metadata."""

    @abstractmethod
    def delete_where(self, name: str, where: dict[str, Any]) -> None:
        """Delete vectors matching metadata filters."""

    @abstractmethod
    def healthy(self) -> bool:
        """True when this backend can be reached."""
