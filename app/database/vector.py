"""Chroma persistent vector store. Used by retrieval when SQL context is empty."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import ROOT_DIR, settings

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self) -> None:
        self._client = None
        self._embed = None

    def _ensure(self) -> None:
        if self._client is not None:
            return
        import chromadb
        from chromadb.utils import embedding_functions

        path = Path(settings.vector_persist_path)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )
        self._embed = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

    def collection_name(self, *, country_id: int | None = None, global_docs: bool = False) -> str:
        prefix = settings.vector_collection_prefix
        if global_docs:
            return f"{prefix}_global"
        if country_id is None:
            return f"{prefix}_default"
        return f"{prefix}_country_{country_id}"

    def get_collection(self, name: str):
        self._ensure()
        return self._client.get_or_create_collection(name=name, embedding_function=self._embed)

    def query(
        self,
        name: str,
        text: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[str]:
        try:
            col = self.get_collection(name)
            kwargs: dict[str, Any] = {"query_texts": [text], "n_results": n_results}
            if where:
                kwargs["where"] = where
            result = col.query(**kwargs)
            docs = (result.get("documents") or [[]])[0]
            return [d for d in docs if d]
        except Exception as exc:
            logger.warning("Vector query failed: %s", exc)
            return []

    def upsert(self, name: str, ids: list[str], documents: list[str], metadatas: list[dict] | None = None) -> None:
        col = self.get_collection(name)
        col.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def delete_where(self, name: str, where: dict[str, Any]) -> None:
        try:
            col = self.get_collection(name)
            col.delete(where=where)
        except Exception as exc:
            logger.warning("Vector delete failed: %s", exc)

    def healthy(self) -> bool:
        try:
            import chromadb
            from pathlib import Path
            from app.core.config import ROOT_DIR, settings

            path = Path(settings.vector_persist_path)
            if not path.is_absolute():
                path = ROOT_DIR / path
            path.mkdir(parents=True, exist_ok=True)
            chromadb.PersistentClient(
                path=str(path),
                settings=chromadb.config.Settings(anonymized_telemetry=False),
            )
            return True
        except Exception as exc:
            logger.warning("Vector store unavailable: %s", exc)
            return False


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    return VectorStore()
