"""
Evaluation orchestration.

Every public method goes through JobManager so concurrent users requesting the
same country/pillar/question share one job and therefore one LLM call.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any

from app.jobs.key_builder import build_key
from app.jobs.manager import job_manager
from app.llm import prompts
from app.llm.json_util import parse_json
from app.llm.router import llm_router
from app.models.evaluation import EvaluationLevel, EvaluationNode, EvaluationState
from app.models.job import Job
from app.repositories.evaluation_repository import evaluation_repository
from app.retrieval.pipeline import retrieval_pipeline

logger = logging.getLogger(__name__)


def _f(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        n = float(value)
        return 0.0 if math.isnan(n) or math.isinf(n) else round(n, 2)
    except (TypeError, ValueError):
        return 0.0


def _i(value: Any) -> int:
    return int(_f(value))


class EvaluationService:
    def __init__(self) -> None:
        self._nodes: dict[str, EvaluationNode] = {}

    def _node_key(self, country_id: int, pillar_id: int | None = None, question_id: int | None = None) -> str:
        return f"{country_id}:{pillar_id}:{question_id}"

    def track(
        self,
        country_id: int,
        state: EvaluationState,
        *,
        pillar_id: int | None = None,
        question_id: int | None = None,
        job_id: str | None = None,
        error: str | None = None,
    ) -> None:
        if question_id is not None:
            level = EvaluationLevel.QUESTION
        elif pillar_id is not None:
            level = EvaluationLevel.PILLAR
        else:
            level = EvaluationLevel.COUNTRY
        key = self._node_key(country_id, pillar_id, question_id)
        self._nodes[key] = EvaluationNode(
            level=level,
            country_id=country_id,
            pillar_id=pillar_id,
            question_id=question_id,
            state=state,
            job_id=job_id,
            error=error,
        )

    def country_progress(self, country_id: int) -> dict[str, Any]:
        nodes = [n for n in self._nodes.values() if n.country_id == country_id]
        by_state: dict[str, int] = {}
        for n in nodes:
            by_state[n.state.value] = by_state.get(n.state.value, 0) + 1
        return {
            "country_id": country_id,
            "counts": by_state,
            "nodes": [n.model_dump() for n in nodes],
        }

    async def analyze_all_countries(self, country_id: int | None = None) -> Job:
        year = datetime.now().year
        key = build_key("evaluation_full", country_id=country_id or 0, year=year)

        async def _run(job: Job) -> dict:
            countries = await evaluation_repository.get_countries(country_id)
            for row in countries:
                cid = int(row["CountryID"])
                await self._analyze_questions(cid, row, job_id=job.id)
                await self._analyze_pillars(cid, row, job_id=job.id)
                await self._analyze_country(cid, row, job_id=job.id)
            return {"countries": len(countries)}

        return await job_manager.submit(
            coalescing_key=key,
            resource_type="evaluation_full",
            executor=_run,
            country_id=country_id,
            year=year,
            purpose="evaluation_country",
        )

    async def analyze_country(self, country_id: int) -> Job:
        year = datetime.now().year
        key = build_key("evaluation_country", country_id=country_id, year=year)

        async def _run(job: Job) -> dict:
            countries = await evaluation_repository.get_countries(country_id)
            for row in countries:
                await self._analyze_country(int(row["CountryID"]), row, job_id=job.id)
            return {"country_id": country_id}

        return await job_manager.submit(
            coalescing_key=key,
            resource_type="evaluation_country",
            executor=_run,
            country_id=country_id,
            year=year,
            purpose="evaluation_country",
        )

    async def analyze_pillars(self, country_id: int, pillar_id: int | None = None) -> Job:
        year = datetime.now().year
        key = build_key("evaluation_pillars", country_id=country_id, pillar_id=pillar_id, year=year)

        async def _run(job: Job) -> dict:
            countries = await evaluation_repository.get_countries(country_id)
            for row in countries:
                await self._analyze_pillars(int(row["CountryID"]), row, pillar_id=pillar_id, job_id=job.id)
            return {"country_id": country_id, "pillar_id": pillar_id}

        return await job_manager.submit(
            coalescing_key=key,
            resource_type="evaluation_pillars",
            executor=_run,
            country_id=country_id,
            pillar_id=pillar_id,
            year=year,
            purpose="evaluation_pillar",
        )

    async def analyze_questions(
        self,
        country_id: int,
        pillar_id: int | None = None,
        missing_only: bool = False,
    ) -> Job:
        year = datetime.now().year
        key = build_key(
            "evaluation_questions",
            country_id=country_id,
            pillar_id=pillar_id,
            year=year,
        )

        async def _run(job: Job) -> dict:
            countries = await evaluation_repository.get_countries(country_id)
            for row in countries:
                await self._analyze_questions(
                    int(row["CountryID"]),
                    row,
                    pillar_id=pillar_id,
                    missing_only=missing_only,
                    job_id=job.id,
                )
            return {"country_id": country_id, "pillar_id": pillar_id}

        return await job_manager.submit(
            coalescing_key=key,
            resource_type="evaluation_questions",
            executor=_run,
            country_id=country_id,
            pillar_id=pillar_id,
            year=year,
            purpose="evaluation_question",
        )

    async def immediate_situation(self, country_id: int) -> Job:
        year = datetime.now().year
        key = build_key("evaluation_immediate", country_id=country_id, year=year)

        async def _run(job: Job) -> dict:
            from app.repositories.chat_repository import chat_repository

            ctx = await chat_repository.get_ai_country_context(country_id, year) or {}
            retrieved = await retrieval_pipeline.for_country_question(
                country_id,
                f"Immediate situation and emerging risks in {ctx.get('CountryName')}",
            )
            result = await llm_router.generate(
                purpose="immediate_situation",
                system=prompts.IMMEDIATE_SYSTEM,
                user=prompts.immediate_user(
                    str(ctx.get("CountryName") or ""),
                    str(ctx.get("Continent") or ""),
                    retrieved.context,
                ),
                job_id=job.id,
            )
            data = parse_json(result.text)
            await evaluation_repository.save_immediate_situation(country_id, year, data)
            return data

        return await job_manager.submit(
            coalescing_key=key,
            resource_type="evaluation_immediate",
            executor=_run,
            country_id=country_id,
            year=year,
            purpose="immediate_situation",
        )

    async def _analyze_questions(
        self,
        country_id: int,
        country: dict,
        pillar_id: int | None = None,
        missing_only: bool = False,
        job_id: str | None = None,
    ) -> None:
        year = datetime.now().year
        rows = await evaluation_repository.get_question_rows(
            country_id, pillar_id, missing_only=missing_only, year=year
        )
        batch: list[dict] = []
        name = country.get("CountryName") or ""
        continent = f"Continent: {country.get('Continent')}, Country: {name}"
        for row in rows:
            qid = int(row["QuestionID"])
            pid = int(row["PillarID"])
            self.track(country_id, EvaluationState.RUNNING, pillar_id=pid, question_id=qid, job_id=job_id)
            retrieved = await retrieval_pipeline.for_country_question(
                country_id, str(row.get("QuestionText") or ""), pid
            )
            try:
                llm = await llm_router.generate(
                    purpose="evaluation_question",
                    system=prompts.QUESTION_SYSTEM,
                    user=prompts.question_user(
                        name,
                        continent,
                        str(row.get("PillarName") or ""),
                        str(row.get("QuestionText") or ""),
                        retrieved.context,
                    ),
                    job_id=job_id,
                )
                ai = parse_json(llm.text)
                normalized = _f(row.get("NormalizedValue"))
                ai_progress = _f(ai.get("AIProgress"))
                evaluator = _f(normalized * 100)
                batch.append(
                    {
                        "CountryID": country_id,
                        "PillarID": pid,
                        "QuestionID": qid,
                        "Year": _i(ai.get("Year") or year),
                        "AIScore": _f(ai.get("AIScore")),
                        "AIProgress": ai_progress,
                        "EvaluatorScore": evaluator,
                        "Discrepancy": abs(ai_progress - evaluator),
                        "ConfidenceLevel": ai.get("ConfidenceLevel"),
                        "EvidenceSummary": ai.get("EvidenceSummary"),
                        "StructuralEvidence": ai.get("StructuralEvidence"),
                        "OperationalEvidence": ai.get("OperationalEvidence"),
                        "OutcomeEvidence": ai.get("OutcomeEvidence"),
                        "PerceptionEvidence": ai.get("PerceptionEvidence"),
                        "TemporalScope": ai.get("TemporalScope"),
                        "DistortionScreening": ai.get("DistortionScreening"),
                        "RelationalDependencies": ai.get("RelationalDependencies"),
                        "StressPoliticalShock": ai.get("StressPoliticalShock"),
                        "StressEconomicShock": ai.get("StressEconomicShock"),
                        "StressNarrativeShock": ai.get("StressNarrativeShock"),
                        "StressOverallResilienceShock": ai.get("StressOverallResilienceShock"),
                        "InequalityAdjustment": ai.get("InequalityAdjustment"),
                        "OpacityRisk": ai.get("OpacityRisk"),
                        "RedFlag": ai.get("RedFlag"),
                        "SourceName": ai.get("SourceName"),
                        "SourceType": ai.get("SourceType"),
                        "SourceURL": ai.get("SourceURL"),
                        "SourceDataYear": _i(ai.get("SourceDataYear")),
                        "SourceHierarchyLevel": _i(ai.get("SourceHierarchyLevel")),
                        "SourceDataExtract": ai.get("SourceDataExtract"),
                        "SourcesConsulted": _i(ai.get("SourcesConsulted")),
                    }
                )
                self.track(country_id, EvaluationState.COMPLETED, pillar_id=pid, question_id=qid, job_id=job_id)
            except Exception as exc:
                logger.exception("Question %s country %s failed", qid, country_id)
                self.track(
                    country_id,
                    EvaluationState.FAILED,
                    pillar_id=pid,
                    question_id=qid,
                    job_id=job_id,
                    error=str(exc),
                )
            if len(batch) >= 5:
                await evaluation_repository.upsert_question_evaluations(batch, country_id)
                batch = []
        if batch:
            await evaluation_repository.upsert_question_evaluations(batch, country_id)
        await evaluation_repository.insert_analytical_layer_results(country_id)

    async def _analyze_pillars(
        self,
        country_id: int,
        country: dict,
        pillar_id: int | None = None,
        job_id: str | None = None,
    ) -> None:
        rows = await evaluation_repository.get_pillar_rows(country_id, pillar_id)
        name = country.get("CountryName") or ""
        continent = f"Continent: {country.get('Continent')}, Country: {name}"
        pillar_batch: list[dict] = []
        source_batch: list[dict] = []
        for row in rows:
            pid = int(row["PillarID"])
            self.track(country_id, EvaluationState.RUNNING, pillar_id=pid, job_id=job_id)
            retrieved = await retrieval_pipeline.for_country_question(
                country_id, f"Pillar assessment {row.get('PillarName')}", pid
            )
            try:
                llm = await llm_router.generate(
                    purpose="evaluation_pillar",
                    system=prompts.PILLAR_SYSTEM,
                    user=prompts.pillar_user(
                        name, continent, str(row.get("PillarName") or ""), retrieved.context
                    ),
                    job_id=job_id,
                )
                ai = parse_json(llm.text)
                ai_progress = _f(ai.get("AIProgress"))
                evaluator = _f(row.get("EvaluatorScore"))
                pillar_batch.append(
                    {
                        "CountryID": country_id,
                        "PillarID": pid,
                        "Year": ai.get("Year") or datetime.now().year,
                        "AIScore": _f(ai.get("AIScore")),
                        "AIProgress": ai_progress,
                        "EvaluatorScore": evaluator,
                        "Discrepancy": abs(ai_progress - evaluator),
                        "ConfidenceLevel": ai.get("ConfidenceLevel"),
                        "EvidenceSummary": ai.get("EvidenceSummary"),
                        "StructuralEvidence": ai.get("StructuralEvidence"),
                        "OperationalEvidence": ai.get("OperationalEvidence"),
                        "OutcomeEvidence": ai.get("OutcomeEvidence"),
                        "PerceptionEvidence": ai.get("PerceptionEvidence"),
                        "TemporalScope": ai.get("TemporalScope"),
                        "DistortionScreening": ai.get("DistortionScreening"),
                        "RelationalIntegrity": ai.get("RelationalIntegrity"),
                        "StressPoliticalShock": ai.get("StressPoliticalShock"),
                        "StressEconomicShock": ai.get("StressEconomicShock"),
                        "StressNarrativeShock": ai.get("StressNarrativeShock"),
                        "StressOverallResilience": ai.get("StressOverallResilience"),
                        "StressScoreAdjustment": ai.get("StressScoreAdjustment"),
                        "InequalityAdjustment": ai.get("InequalityAdjustment"),
                        "OpacityRisk": ai.get("OpacityRisk"),
                        "NonCompensationNote": ai.get("NonCompensationNote"),
                        "GeographicEquityNote": ai.get("GeographicEquityNote"),
                        "InstitutionalAssessment": ai.get("InstitutionalAssessment"),
                        "DataGapAnalysis": ai.get("DataGapAnalysis"),
                        "RedFlag": ai.get("RedFlag"),
                    }
                )
                for src in ai.get("Sources") or []:
                    source_batch.append(
                        {
                            "CountryID": country_id,
                            "PillarID": pid,
                            "DataYear": _i(src.get("data_year")),
                            "SourceType": src.get("source_type"),
                            "SourceName": src.get("source_name"),
                            "SourceURL": src.get("source_url"),
                            "DataExtract": src.get("data_extract"),
                            "TrustLevel": _i(src.get("source_trust_level")),
                        }
                    )
                self.track(country_id, EvaluationState.COMPLETED, pillar_id=pid, job_id=job_id)
            except Exception as exc:
                logger.exception("Pillar %s country %s failed", pid, country_id)
                self.track(
                    country_id, EvaluationState.FAILED, pillar_id=pid, job_id=job_id, error=str(exc)
                )
        if pillar_batch:
            await evaluation_repository.upsert_pillar_evaluations(pillar_batch, source_batch)
        await evaluation_repository.recalculate_country_score(country_id)

    async def _analyze_country(self, country_id: int, country: dict, job_id: str | None = None) -> None:
        rows = await evaluation_repository.get_country_eval_rows(country_id)
        name = country.get("CountryName") or ""
        continent = f"Continent: {country.get('Continent')}, Country: {name}"
        self.track(country_id, EvaluationState.RUNNING, job_id=job_id)
        retrieved = await retrieval_pipeline.for_country_question(
            country_id, f"Country-level peace assessment for {name}"
        )
        llm = await llm_router.generate(
            purpose="evaluation_country",
            system=prompts.COUNTRY_SYSTEM,
            user=prompts.country_user(name, continent, retrieved.context),
            job_id=job_id,
        )
        ai = parse_json(llm.text)
        batch = []
        for row in rows or [{"CountryID": country_id, "EvaluatorScore": 0}]:
            ai_progress = _f(ai.get("AIProgress"))
            evaluator = _f(row.get("EvaluatorScore"))
            batch.append(
                {
                    "CountryID": country_id,
                    "Year": _i(ai.get("Year") or datetime.now().year),
                    "AIScore": _f(ai.get("AIScore")),
                    "AIProgress": ai_progress,
                    "EvaluatorScore": evaluator,
                    "Discrepancy": abs(ai_progress - evaluator),
                    "ConfidenceLevel": ai.get("ConfidenceLevel", "Unknown"),
                    "EvidenceSummary": ai.get("ExecutiveSummary"),
                    "StructuralEvidence": ai.get("StructuralEvidence"),
                    "OperationalEvidence": ai.get("OperationalEvidence"),
                    "OutcomeEvidence": ai.get("OutcomeEvidence"),
                    "PerceptionEvidence": ai.get("PerceptionEvidence"),
                    "TemporalScope": ai.get("TemporalScope"),
                    "DistortionScreening": ai.get("DistortionScreening"),
                    "PoliticalShock": ai.get("PoliticalShock"),
                    "EconomicShock": ai.get("EconomicShock"),
                    "NarrativeShock": ai.get("NarrativeShock"),
                    "OverallStressResilience": ai.get("OverallStressResilience"),
                    "StressScoreAdjustment": ai.get("StressScoreAdjustment"),
                    "InequalityAdjustment": ai.get("InequalityAdjustment"),
                    "OpacityRisk": ai.get("OpacityRisk"),
                    "NonCompensationNote": ai.get("NonCompensationNote"),
                    "CrossPillarPatterns": ai.get("CrossPillarPatterns"),
                    "RelationalIntegrity": ai.get("RelationalIntegrity"),
                    "InstitutionalCapacity": ai.get("InstitutionalCapacity"),
                    "EquityAssessment": ai.get("EquityAssessment"),
                    "ConflictRiskOutlook": ai.get("ConflictRiskOutlook"),
                    "StrategicRecommendation": ai.get("StrategicRecommendation"),
                    "DataTransparencyNote": ai.get("DataTransparencyNote"),
                    "PrimarySource": ai.get("PrimarySource"),
                }
            )
        if batch:
            await evaluation_repository.upsert_country_evaluations(batch)
        await evaluation_repository.recalculate_country_score(country_id)
        self.track(country_id, EvaluationState.COMPLETED, job_id=job_id)


evaluation_service = EvaluationService()
