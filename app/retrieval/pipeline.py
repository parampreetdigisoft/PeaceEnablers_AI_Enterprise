"""Retrieval order: SQL → vector → web fallback."""

from __future__ import annotations

from dataclasses import dataclass

from app.retrieval.question_scope import plan_retrieval
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
        plan = plan_retrieval(question, country_id)
        sql_text, meta = ("", {})
        if plan.search_country_id and not plan.search_all_countries:
            sql_text, meta = await sql_retriever.country_question_context(
                country_id, question, pillar_id, faq_id
            )
        country_name = str(meta.get("CountryName") or "")
        pillar_name = str(meta.get("PillarName") or "")
        vector_text = await vector_retriever.collect(
            plan, question, pillar_id if plan.search_country_id else None
        )

        parts = [part for part in (sql_text, vector_text) if not _thin(part)]
        if parts:
            source = "vector" if not _thin(vector_text) else "sql"
            return RetrievalResult("\n\n".join(parts), source, country_name, pillar_name)

        web_text = await web_fallback.search(question)
        if web_text:
            return RetrievalResult(web_text, "web", country_name, pillar_name)
        return RetrievalResult(sql_text or "", "none", country_name, pillar_name)

    async def for_global_question(self, question: str, faq_id: int | None = None) -> RetrievalResult:
        plan = plan_retrieval(question, None)
        sql_text = ""
        if plan.search_platform and not plan.search_all_countries:
            sql_text = await sql_retriever.global_question_context(question, faq_id)
        vector_text = await vector_retriever.collect(plan, question)
        parts = [part for part in (sql_text, vector_text) if not _thin(part)]
        if parts:
            source = "vector" if not _thin(vector_text) else "sql"
            return RetrievalResult("\n\n".join(parts), source, "global", "")
        web_text = await web_fallback.search(question)
        if web_text:
            return RetrievalResult(web_text, "web", "global", "")
        return RetrievalResult(sql_text or "", "none", "global", "")


retrieval_pipeline = RetrievalPipeline()
