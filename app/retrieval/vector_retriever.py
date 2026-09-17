"""Vector retrieval when SQL context is thin."""

from __future__ import annotations

from app.core.config import settings
from app.services.embedding_service import get_embedding_service
from app.vectorstores.factory import get_vector_store


class VectorRetriever:
    def search_country(self, country_id: int, question: str, pillar_id: int | None = None) -> str:
        store = get_vector_store()
        name = store.collection_name(country_id=country_id)
        where = {"pillar_id": {"$eq": pillar_id}} if pillar_id is not None else None
        embedding = get_embedding_service().embed_text(question)
        chunks = store.query(name, embedding, n_results=settings.top_k_results, where=where)
        return "\n\n".join(chunks)

    def search_global(self, question: str) -> str:
        store = get_vector_store()
        name = store.collection_name(global_docs=True)
        embedding = get_embedding_service().embed_text(question)
        chunks = store.query(name, embedding, n_results=settings.top_k_results)
        return "\n\n".join(chunks)


vector_retriever = VectorRetriever()
