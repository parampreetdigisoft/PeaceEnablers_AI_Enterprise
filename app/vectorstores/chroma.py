"""Chroma persistent vector store. The only module that may import chromadb."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.config import ROOT_DIR, settings
from app.vectorstores.base import VectorStore

logger = logging.getLogger(__name__)


class ChromaVectorStore(VectorStore):
    def __init__(self) -> None:
        self._client = None

    def _persist_path(self) -> Path:
        path = Path(settings.vector_persist_path)
        if not path.is_absolute():
            path = ROOT_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure(self) -> None:
        if self._client is not None:
            return
        import chromadb

        path = self._persist_path()
        self._client = chromadb.PersistentClient(
            path=str(path),
            settings=chromadb.config.Settings(anonymized_telemetry=False),
        )

    def _collection(self, name: str):
        self._ensure()
        # embedding_function=None: embeddings are supplied by EmbeddingService.
        # Existing collections created with SentenceTransformerEmbeddingFunction stay readable.
        return self._client.get_or_create_collection(name=name, embedding_function=None)

    def query(
        self,
        name: str,
        embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[str]:
        return [
            record["text"]
            for record in self.query_records(name, embedding, n_results=n_results, where=where)
        ]

    def query_records(
        self,
        name: str,
        embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            self._ensure()
            # get_collection does not create an empty collection for a country
            # that has never had a document.
            col = self._client.get_collection(name=name)
            kwargs: dict[str, Any] = {
                "query_embeddings": [embedding],
                "n_results": max(1, n_results),
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                kwargs["where"] = where
            result = col.query(**kwargs)
            docs = (result.get("documents") or [[]])[0] or []
            metas = (result.get("metadatas") or [[]])[0] or []
            distances = (result.get("distances") or [[]])[0] or []
            records: list[dict[str, Any]] = []
            for idx, text in enumerate(docs):
                if not text:
                    continue
                records.append(
                    {
                        "text": text,
                        "distance": distances[idx] if idx < len(distances) else None,
                        "metadata": metas[idx] if idx < len(metas) and metas[idx] else {},
                    }
                )
            return records
        except Exception as exc:
            logger.warning("Vector query failed: %s", exc)
            return []

    def upsert(
        self,
        name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        col = self._collection(name)
        col.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def delete_where(self, name: str, where: dict[str, Any]) -> None:
        try:
            col = self._collection(name)
            col.delete(where=where)
        except Exception as exc:
            logger.warning("Vector delete failed: %s", exc)

    def healthy(self) -> bool:
        try:
            import chromadb

            path = self._persist_path()
            chromadb.PersistentClient(
                path=str(path),
                settings=chromadb.config.Settings(anonymized_telemetry=False),
            )
            return True
        except Exception as exc:
            logger.warning("Vector store unavailable: %s", exc)
            return False
