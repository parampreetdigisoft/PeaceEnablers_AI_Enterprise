"""Vector retrieval when SQL context is thin.

Collections:
- pem_global: platform documents (how the product works, where to find a feature)
- pem_country_{id}: documents that belong only to that country
"""

from __future__ import annotations

from app.core.config import settings
from app.repositories.document_repository import document_repository
from app.retrieval.question_scope import RetrievalPlan
from app.services.embedding_service import get_embedding_service
from app.vectorstores.factory import get_vector_store


def _format_hits(records: list[dict], label: str) -> str:
    lines: list[str] = []
    for record in records:
        meta = record.get("metadata") or {}
        doc_id = meta.get("country_doc_id", "")
        country_id = meta.get("country_id") or ""
        country_name = meta.get("country_name") or ""
        model = meta.get("embedding_model") or ""
        ingested = meta.get("ingested_at") or ""
        header = (
            f"[{label} country_id={country_id} country={country_name} "
            f"source_document_id={doc_id} ingested_at={ingested} embedding_model={model}]"
        )
        lines.append(f"{header}\n{record.get('text') or ''}")
    return "\n\n".join(lines)


class VectorRetriever:
    def search_country(self, country_id: int, question: str, pillar_id: int | None = None) -> str:
        store = get_vector_store()
        name = store.collection_name(country_id=country_id)
        where = {"pillar_id": {"$eq": pillar_id}} if pillar_id is not None else None
        embedding = get_embedding_service().embed_text(question)
        records = store.query_records(name, embedding, n_results=settings.top_k_results, where=where)
        return _format_hits(records, "country-document")

    def search_global(self, question: str) -> str:
        store = get_vector_store()
        name = store.collection_name(global_docs=True)
        embedding = get_embedding_service().embed_text(question)
        records = store.query_records(name, embedding, n_results=settings.top_k_results)
        return _format_hits(records, "platform-document")

    async def search_all_countries(self, question: str) -> str:
        """Search each country collection that has uploaded files. Skip empty countries."""
        countries = await document_repository.list_countries_with_documents()
        if not countries:
            return ""

        store = get_vector_store()
        embedding = get_embedding_service().embed_text(question)
        hits: list[dict] = []
        per_country = 2
        for country in countries:
            country_id = int(country["CountryID"])
            name = store.collection_name(country_id=country_id)
            for record in store.query_records(name, embedding, n_results=per_country):
                meta = dict(record.get("metadata") or {})
                meta.setdefault("country_id", country_id)
                meta.setdefault("country_name", country.get("CountryName") or "")
                record = {**record, "metadata": meta}
                hits.append(record)

        hits.sort(key=lambda item: item.get("distance") if item.get("distance") is not None else 1)
        return _format_hits(hits[: settings.top_k_results], "country-document")

    async def collect(self, plan: RetrievalPlan, question: str, pillar_id: int | None = None) -> str:
        blocks: list[str] = []
        if plan.search_platform:
            text = self.search_global(question)
            if text.strip():
                blocks.append(
                    "Platform documents. Use these for how the product works and where to find a feature:\n"
                    + text
                )
        if plan.search_country_id:
            text = self.search_country(plan.search_country_id, question, pillar_id)
            if text.strip():
                blocks.append(
                    f"Documents stored only for country_id={plan.search_country_id}. "
                    "Do not apply these to any other country:\n" + text
                )
        if plan.search_all_countries:
            text = await self.search_all_countries(question)
            if text.strip():
                blocks.append(
                    "Local documents searched across every country that has files. "
                    "Name the country on each source. A file from one country is not evidence for another:\n"
                    + text
                )
        return "\n\n".join(blocks)


vector_retriever = VectorRetriever()
