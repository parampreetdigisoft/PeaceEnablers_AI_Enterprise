"""Chat / Q&A. Retrieval is SQL → vector → web. Identical in-flight questions coalesce."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.jobs.key_builder import build_key
from app.jobs.manager import job_manager
from app.llm import prompts
from app.llm.json_util import parse_json
from app.llm.router import llm_router
from app.models.job import Job
from app.retrieval.pipeline import retrieval_pipeline
from app.retrieval.sql_retriever import sql_retriever


class ChatService:

    async def answer_country(
        self,
        country_id: int,
        question: str,
        history: str | None = None,
        faq_id: int | None = None,
        pillar_id: int | None = None,
    ) -> str:
        key = build_key(
            "chat",
            country_id=country_id,
            pillar_id=pillar_id,
            question_text=question,
        )

        async def _run(job: Job) -> str:
            retrieved = await retrieval_pipeline.for_country_question(
                country_id, question, pillar_id, faq_id
            )
            llm = await llm_router.generate(
                purpose="chat",
                system=prompts.CHAT_SYSTEM,
                user=prompts.chat_user(
                    question, retrieved.context, retrieved.country_name, retrieved.pillar_name, history
                ),
                job_id=job.id,
            )
            return llm.text

        job = await job_manager.submit(
            coalescing_key=key,
            resource_type="chat",
            executor=_run,
            country_id=country_id,
            pillar_id=pillar_id,
            wait=True,
            purpose="chat",
        )
        return str(job.result or "")

    async def answer_global(self, question: str, history: str | None = None, faq_id: int | None = None) -> str:
        key = build_key("chat_global", question_text=question)

        async def _run(job: Job) -> str:
            retrieved = await retrieval_pipeline.for_global_question(question, faq_id)
            llm = await llm_router.generate(
                purpose="chat",
                system=prompts.CHAT_SYSTEM,
                user=prompts.chat_user(question, retrieved.context, "global", "", history),
                job_id=job.id,
            )
            return llm.text

        job = await job_manager.submit(
            coalescing_key=key,
            resource_type="chat_global",
            executor=_run,
            wait=True,
            purpose="chat",
        )
        return str(job.result or "")

    async def answer_comparison(
        self,
        question: str,
        country_ids: list[int],
        history: str | None = None,
    ) -> str:
        key = build_key("chat_comparison", country_ids=country_ids, question_text=question)

        async def _run(job: Job) -> str:
            context = await sql_retriever.comparison_context(country_ids)
            llm = await llm_router.generate(
                purpose="comparison",
                system=prompts.CHAT_SYSTEM,
                user=prompts.chat_user(question, context, "comparison", "", history),
                job_id=job.id,
            )
            return llm.text

        job = await job_manager.submit(
            coalescing_key=key,
            resource_type="chat_comparison",
            executor=_run,
            wait=True,
            purpose="comparison",
        )
        return str(job.result or "")

    async def executive_slides(self, country_id: int) -> dict[str, Any]:
        question = "Produce executive intelligence slides: daily, weekly, monthly performance, combined risks, early warnings."
        answer = await self.answer_country(country_id, question)
        try:
            parsed = parse_json(answer)
            parsed.setdefault("countryId", country_id)
            return {"success": True, "message": "ok", "result": parsed}
        except Exception:
            return {
                "success": True,
                "message": "ok",
                "result": {
                    "countryId": country_id,
                    "countryName": "",
                    "dailyPerformance": {"trend": "n/a", "summary": answer[:500]},
                    "weeklyPerformance": {"trend": "n/a", "summary": ""},
                    "monthlyPerformance": {"trend": "n/a", "summary": ""},
                    "combinedRisks": [],
                    "earlyWarnings": [],
                },
            }

    async def summarize_kpi(self, payload: dict[str, Any]) -> dict[str, Any]:
        system = (
            "Summarize KPI performance for an end user. Return JSON with keys: "
            "summary, scoreInterpretation, keyTakeaways (array), outlook."
        )
        user = (
            f"Country: {payload.get('countryName')}\n"
            f"Layer: {payload.get('layerName')} ({payload.get('layerCode')})\n"
            f"Purpose: {payload.get('purpose')}\n"
            f"Manual score: {payload.get('manualScore')} ({payload.get('manualCondition')})\n"
            f"AI score: {payload.get('aiScore')} ({payload.get('aiCondition')})\n"
            f"Bands: {payload.get('interpretationBands')}\n"
            f"Category: {payload.get('categoryDetails')}\n"
        )
        llm = await llm_router.generate(purpose="kpi_lookup", system=system, user=user)
        try:
            result = parse_json(llm.text)
        except Exception:
            result = {"summary": llm.text, "keyTakeaways": [], "outlook": None, "scoreInterpretation": None}
        return {"success": True, "message": "KPI summary generated successfully", "result": result}

    async def emerging_trends(self, country_count: int, query_variant: int | None) -> dict[str, Any]:
        llm = await llm_router.generate(
            purpose="chat",
            system="Return JSON: updatedAt (ISO), headline, subHeadline, countries (array of cards).",
            user=f"Generate {country_count} emerging global risk/trend cards. variant={query_variant}",
        )
        try:
            result = parse_json(llm.text)
        except Exception:
            result = {
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "headline": "Emerging trends",
                "subHeadline": "Live feed unavailable; showing placeholder.",
                "countries": [],
            }
        return {"success": True, "message": "ok", "result": result}

    async def pillar_live_signals(self) -> dict[str, Any]:
        llm = await llm_router.generate(
            purpose="chat",
            system="Return JSON: updatedAt, headline, subHeadline, pillars (exactly 23 cards with pillarId 1-23).",
            user="One live signal per Peace Enabler pillar (IDs 1-23).",
        )
        try:
            result = parse_json(llm.text)
        except Exception:
            result = {
                "updatedAt": datetime.now(timezone.utc).isoformat(),
                "headline": "Pillar signals",
                "subHeadline": "Live feed unavailable.",
                "pillars": [],
            }
        return {"success": True, "message": "ok", "result": result}

chat_service = ChatService()
