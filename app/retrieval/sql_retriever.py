"""SQL-first context: FAQs, country scores, stored-procedure local context."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.repositories.chat_repository import chat_repository


def _stringify(data: Any) -> str:
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        return "\n".join(f"{k}: {v}" for k, v in data.items() if v not in (None, ""))
    if isinstance(data, list):
        return "\n\n".join(_stringify(item) for item in data)
    return str(data)


class SqlRetriever:
    async def country_question_context(
        self,
        country_id: int,
        question_text: str,
        pillar_id: int | None,
        faq_id: int | None,
    ) -> tuple[str, dict[str, Any]]:
        year = datetime.now().year
        meta = await chat_repository.get_ai_country_context(country_id, year, pillar_id) or {}
        if faq_id is not None:
            local = await chat_repository.get_local_context([faq_id], country_id, pillar_id)
            return _stringify(local) or _stringify(meta), meta

        faqs = await chat_repository.get_faq_context(is_global=False)
        matched = _match_faqs(question_text, faqs)
        if matched:
            local = await chat_repository.get_local_context(matched[:3], country_id, pillar_id)
            if local:
                return _stringify(local), meta
        return _stringify(meta), meta

    async def global_question_context(self, question_text: str, faq_id: int | None) -> str:
        if faq_id is not None:
            local = await chat_repository.get_local_context([faq_id])
            return _stringify(local)
        faqs = await chat_repository.get_faq_context(is_global=True)
        matched = _match_faqs(question_text, faqs)
        if matched:
            local = await chat_repository.get_local_context(matched[:3])
            return _stringify(local)
        return ""

    async def comparison_context(self, country_ids: list[int]) -> str:
        rows = await chat_repository.get_cross_comparison_context(country_ids)
        names = await chat_repository.get_country_names(country_ids)
        return _stringify(names) + "\n\n" + _stringify(rows)


def _match_faqs(question: str, faqs: list[dict[str, Any]]) -> list[Any]:
    q = question.lower()
    scored: list[tuple[int, Any]] = []
    for faq in faqs:
        text = str(faq.get("QuestionText") or "").lower()
        overlap = sum(1 for token in q.split() if len(token) > 3 and token in text)
        if overlap:
            scored.append((overlap, faq.get("FAQID")))
    scored.sort(reverse=True)
    return [faq_id for _, faq_id in scored if faq_id is not None]


sql_retriever = SqlRetriever()
