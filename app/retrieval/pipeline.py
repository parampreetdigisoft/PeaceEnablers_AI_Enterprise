"""Retrieval order: SQL → vector → web fallback."""

from __future__ import annotations

from dataclasses import dataclass

from app.retrieval.sql_retriever import sql_retriever
from app.retrieval.vector_retriever import vector_retriever
from app.retrieval.web_fallback import web_fallback


@dataclass
class RetrievalResult:
    context: str
    source: str
    country_name: str = ""
    pillar_name: str = ""


def _thin(text: str) -> bool:
    return len((text or "").strip()) < 40


class RetrievalPipeline:
    async def for_country_question(
        self,
        country_id: int,
        question: str,
        pillar_id: int | None = None,
        faq_id: int | None = None,
    ) -> RetrievalResult:
        sql_text, meta = await sql_retriever.country_question_context(
            country_id, question, pillar_id, faq_id
        )
        country_name = str(meta.get("CountryName") or "")
        pillar_name = str(meta.get("PillarName") or "")
        if not _thin(sql_text):
            return RetrievalResult(sql_text, "sql", country_name, pillar_name)

        vector_text = vector_retriever.search_country(country_id, question, pillar_id)
        if not _thin(vector_text):
            combined = (sql_text + "\n\n" + vector_text).strip()
            return RetrievalResult(combined, "vector", country_name, pillar_name)

        web_text = await web_fallback.search(question)
        if web_text:
            return RetrievalResult(web_text, "web", country_name, pillar_name)
        return RetrievalResult(
            sql_text, "none" if _thin(sql_text) else "sql", country_name, pillar_name
        )

    async def for_global_question(self, question: str, faq_id: int | None = None) -> RetrievalResult:
        sql_text = await sql_retriever.global_question_context(question, faq_id)
        if not _thin(sql_text):
            return RetrievalResult(sql_text, "sql", "global", "")
        vector_text = vector_retriever.search_global(question)
        if not _thin(vector_text):
            return RetrievalResult(vector_text, "vector", "global", "")
        web_text = await web_fallback.search(question)
        if web_text:
            return RetrievalResult(web_text, "web", "global", "")
        return RetrievalResult(sql_text or "", "none", "global", "")


retrieval_pipeline = RetrievalPipeline()
