"""Shared embedding model. Vector backends never generate embeddings themselves."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self._model = None

    def _ensure(self) -> None:
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer

        model_name = settings.vector_embedding_model
        logger.info("Loading embedding model %s", model_name)
        self._model = SentenceTransformer(model_name)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        self._ensure()
        vectors = self._model.encode(
            list(texts),
            convert_to_numpy=True,
            normalize_embeddings=settings.vector_embedding_normalize,
        )
        return [v.tolist() for v in vectors]


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
