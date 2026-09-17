"""Select the vector backend from VECTOR_DB. RAG code never imports a backend here."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.vectorstores.base import VectorStore


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStore:
    backend = (settings.vector_db or "chroma").strip().lower()
    if backend == "chroma":
        from app.vectorstores.chroma import ChromaVectorStore

        return ChromaVectorStore()

    # Live Pinecone switch — uncomment after installing the commented pinecone
    # package in requirements.txt and filling PINECONE_* in .env:
    # if backend == "pinecone":
    #     from app.vectorstores.pinecone import PineconeVectorStore
    #     return PineconeVectorStore()

    if backend == "pinecone":
        raise ValueError(
            "Pinecone is prepared but not enabled. Uncomment pinecone in "
            "requirements.txt, install it, uncomment PineconeVectorStore in "
            "app/vectorstores/pinecone.py, and uncomment the factory branch above."
        )

    raise ValueError(f"Unsupported vector database: {settings.vector_db}")
