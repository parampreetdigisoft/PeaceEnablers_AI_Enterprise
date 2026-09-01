"""SQL for country / pillar / question evaluations. Only this module talks to session.py for eval data."""

from __future__ import annotations

import json
from typing import Any

from app.database.session import db_session


class EvaluationRepository:
    async def get_countries(self, country_id: int | None = None) -> list[dict[str, Any]]:
        if country_id is not None:
            return await db_session.fetch_dicts(
                "SELECT CountryID, CountryName, Continent FROM Countries WHERE IsDeleted = 0 AND CountryID = ?",
                (country_id,),
            )
        return await db_session.fetch_dicts(
            "SELECT CountryID, CountryName, Continent FROM Countries WHERE IsDeleted = 0"
        )

    async def get_question_rows(
        self,
        country_id: int,
        pillar_id: int | None = None,
        missing_only: bool = False,
        year: int | None = None,
    ) -> list[dict[str, Any]]:
        where = "CountryID = ?"
        params: list[Any] = [country_id]
        if pillar_id is not None:
            where += " AND PillarID = ?"
            params.append(pillar_id)
        if missing_only and year is not None:
            where += """
                AND QuestionID NOT IN (
                    SELECT QuestionID FROM AIEstimatedQuestionScores WHERE Year = ?
                )
            """
            params.append(year)
        query = f"SELECT * FROM vw_AiCountryPillarQuestionEvaluations WHERE {where}"
        return await db_session.fetch_dicts(query, tuple(params))

    async def get_pillar_rows(self, country_id: int, pillar_id: int | None = None) -> list[dict[str, Any]]:
        where = "countryId = ?"
        params: list[Any] = [country_id]
        if pillar_id is not None:
            where += " AND PillarID = ?"
            params.append(pillar_id)
        return await db_session.fetch_dicts(
            f"SELECT * FROM vw_AiCountryPillarEvaluation WHERE {where}",
            tuple(params),
        )

    async def get_country_eval_rows(self, country_id: int) -> list[dict[str, Any]]:
        return await db_session.fetch_dicts(
            "SELECT * FROM vw_AiCountryEvaluations WHERE countryId = ?",
            (country_id,),
        )

    async def upsert_question_evaluations(self, rows: list[dict], country_id: int) -> None:
        if not rows:
            return
        await db_session.execute_sp(
            "{CALL usp_AiBulkUpsertPillarQuestionCountryEvaluations (?)}",
            (json.dumps(rows),),
        )
        await self.recalculate_country_score(country_id)

    async def upsert_pillar_evaluations(self, rows: list[dict], sub_rows: list[dict]) -> None:
        if not rows:
            return
        await db_session.execute_sp(
            "{CALL usp_AiBulkUpsertCountryPillarEvaluations (?, ?)}",
            (json.dumps(rows), json.dumps(sub_rows or [])),
        )

    async def upsert_country_evaluations(self, rows: list[dict]) -> None:
        if not rows:
            return
        await db_session.execute_sp(
            "EXEC usp_AiBulkUpsertCountryEvaluations @CountryEvaluations = ?",
            (json.dumps(rows),),
        )

    async def recalculate_country_score(self, country_id: int) -> None:
        await db_session.execute_sp("EXEC sp_AiRecalculateCountryScore @CountryID = ?", (country_id,))

    async def insert_analytical_layer_results(self, country_id: int) -> None:
        await db_session.execute_sp("EXEC sp_AiInsertAnalyticalLayerResults @CountryID = ?", (country_id,))

    async def save_immediate_situation(self, country_id: int, year: int, record: dict) -> None:
        exec_summary = record.get("executive_summary")
        query = """
            UPDATE AICountryScores
            SET ImmediateSituationSummary = ?, KeyDevelopments = ?, CriticalRisks = ?,
                Gaps = ?, KeyFindings = ?, Recommendations = ?,
                EvidenceSummary = CASE
                    WHEN ? IS NOT NULL AND LTRIM(RTRIM(CAST(? AS NVARCHAR(MAX)))) <> ''
                    THEN ? ELSE EvidenceSummary END
            WHERE CountryID = ? AND Year = ?
        """
        await db_session.execute_write(
            query,
            (
                record.get("immediateSituationSummary"),
                record.get("key_developments"),
                record.get("critical_risks"),
                record.get("gaps"),
                record.get("key_findings"),
                record.get("recommendations"),
                exec_summary,
                exec_summary,
                exec_summary,
                country_id,
                year,
            ),
        )


evaluation_repository = EvaluationRepository()
