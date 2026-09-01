"""Country / pillar / question evaluation — same paths as PeaceEnablers_AI_Service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import analyst_user
from app.core.security import UserContext
from app.schemas.evaluation import AnalysisResponse, MissingPillarQuestionRequest
from app.services.evaluation_service import evaluation_service

router = APIRouter(
    prefix="/api/countries-score-analysis",
    tags=["Score Analysis"],
    dependencies=[Depends(analyst_user)],
)


def _accepted(job) -> AnalysisResponse:
    verb = "already running — attached to existing job" if job.attached else "started"
    return AnalysisResponse(
        success=True,
        message=f"Analysis {verb}. Processing in background.",
        jobId=job.id,
        coalesced=job.attached,
        data={"status": job.status.value, "key": job.coalescing_key},
    )


@router.post("/analyze/full", response_model=AnalysisResponse)
async def analyze_all_countries_full(_: UserContext = Depends(analyst_user)):
    job = await evaluation_service.analyze_all_countries()
    return _accepted(job)


@router.post("/analyze/missing-pillar-questions", response_model=AnalysisResponse)
async def analyze_missing_pillar_questions(
    request: MissingPillarQuestionRequest,
    _: UserContext = Depends(analyst_user),
):
    job = await evaluation_service.analyze_questions(
        request.countryID, request.pillarID, missing_only=True
    )
    return _accepted(job)


@router.post("/analyze/{country_id}/full", response_model=AnalysisResponse)
async def analyze_single_country_full(country_id: int, _: UserContext = Depends(analyst_user)):
    if not country_id:
        raise HTTPException(status_code=400, detail="Country ID is required")
    job = await evaluation_service.analyze_all_countries(country_id)
    return _accepted(job)


@router.post("/analyze/{country_id}", response_model=AnalysisResponse)
async def analyze_single_country(country_id: int, _: UserContext = Depends(analyst_user)):
    if not country_id:
        raise HTTPException(status_code=400, detail="Country ID is required")
    job = await evaluation_service.analyze_country(country_id)
    return _accepted(job)


@router.post("/analyze/{country_id}/pillars", response_model=AnalysisResponse)
async def analyze_country_pillars(country_id: int, _: UserContext = Depends(analyst_user)):
    if not country_id:
        raise HTTPException(status_code=400, detail="Country ID is required")
    job = await evaluation_service.analyze_pillars(country_id)
    return _accepted(job)


@router.post("/analyze/{country_id}/questions", response_model=AnalysisResponse)
async def analyze_questions_of_country(country_id: int, _: UserContext = Depends(analyst_user)):
    if not country_id:
        raise HTTPException(status_code=400, detail="Country ID is required")
    job = await evaluation_service.analyze_questions(country_id)
    return _accepted(job)


@router.post("/analyze/{country_id}/pillars/{pillar_id}/questions", response_model=AnalysisResponse)
async def analyze_questions_of_country_pillar(
    country_id: int, pillar_id: int, _: UserContext = Depends(analyst_user)
):
    if not country_id:
        raise HTTPException(status_code=400, detail="Country ID is required")
    job = await evaluation_service.analyze_questions(country_id, pillar_id)
    return _accepted(job)


@router.post("/analyze/{country_id}/single-pillar/{pillar_id}", response_model=AnalysisResponse)
async def analyze_single_pillar(
    country_id: int, pillar_id: int, _: UserContext = Depends(analyst_user)
):
    if not country_id or not pillar_id:
        raise HTTPException(status_code=400, detail="provide required parameter")
    job = await evaluation_service.analyze_pillars(country_id, pillar_id)
    return _accepted(job)


@router.post("/analyze/{country_id}/immediateSituation", response_model=AnalysisResponse)
async def analyze_immediate_situation(country_id: int, _: UserContext = Depends(analyst_user)):
    if not country_id:
        raise HTTPException(status_code=400, detail="provide required parameter")
    job = await evaluation_service.immediate_situation(country_id)
    return _accepted(job)
