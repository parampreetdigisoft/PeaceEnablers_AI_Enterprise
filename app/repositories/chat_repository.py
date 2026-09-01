"""Country context and FAQ reads used by chat / retrieval."""

from __future__ import annotations

import json
from typing import Any

from app.database.session import db_session


class ChatRepository:
    async def get_ai_country_context(
        self,
        country_id: int,
        year: int,
        pillar_id: int | None = None,
    ) -> dict[str, Any] | None:
        query = """
            SELECT
                a.AIProgress as PeaceEnablerScore,
                c.CountryName,
                c.Continent,
                a.EvidenceSummary,
                a.StructuralEvidence,
                a.OutcomeEvidence,
                a.PerceptionEvidence,
                a.CrossPillarPatterns,
                a.StrategicRecommendation,
                a.TemporalScope,
                a.DistortionScreening,
                a.PoliticalShock,
                a.EconomicShock,
                a.NarrativeShock,
                a.RelationalIntegrity,
                a.InstitutionalCapacity,
                a.EquityAssessment,
                a.ConflictRiskOutlook,
                a.PrimarySource,
                a.DataTransparencyNote,
                p.PillarName
            FROM Countries c
            LEFT JOIN AICountryScores a ON a.CountryID = c.CountryID AND a.Year = ?
            LEFT JOIN pillars p ON p.PillarID = ?
            WHERE c.IsDeleted = 0 AND c.CountryID = ?
        """
        rows = await db_session.fetch_dicts(query, (year, pillar_id, country_id))
        return rows[0] if rows else None

    async def get_faq_context(self, is_global: bool = False) -> list[dict[str, Any]]:
        related = "global" if is_global else "country"
        return await db_session.fetch_dicts(
            "SELECT FAQID, Related, Category, QuestionText FROM AIAssistantFAQ WHERE Related LIKE ?",
            (related,),
        )

    async def get_local_context(
        self,
        faq_ids: list[Any],
        country_id: int | None = None,
        pillar_id: int | None = None,
    ) -> list[dict[str, Any]]:
        return await db_session.fetch_dicts(
            "EXEC dbo.usp_GetLocalContextDataForLLM ?, ?, ?",
            (json.dumps(faq_ids), country_id, pillar_id),
        )

    async def get_cross_comparison_context(self, country_ids: list[int]) -> list[dict[str, Any]]:
        return await db_session.fetch_dicts(
            "EXEC dbo.usp_CountryCrossComparision_faq ?",
            (json.dumps(country_ids),),
        )

    async def get_country_names(self, country_ids: list[int]) -> list[dict[str, Any]]:
        if not country_ids:
            return []
        placeholders = ",".join("?" for _ in country_ids)
        return await db_session.fetch_dicts(
            f"SELECT CountryID, CountryName, Continent FROM Countries WHERE CountryID IN ({placeholders})",
            tuple(country_ids),
        )


chat_repository = ChatRepository()
