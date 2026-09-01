"""Chat endpoints — same paths as PeaceEnablers_AI_Service /api/chat/*."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import analyst_user
from app.core.security import UserContext
from app.schemas.chat import (
    ChatCountryExecutiveSlidesRequest,
    ChatCountryExecutiveSlidesResponse,
    ChatCountryRequest,
    ChatCrossComparisionRequest,
    ChatEmergingTrendsResponse,
    ChatGlobalRequest,
    ChatPillarLiveSignalsResponse,
    ChatRequest,
    ChatResponse,
    KpiSummaryRequest,
    KpiSummaryResponse,
    KpiSummaryResult,
)
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(analyst_user)])


@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest, _: UserContext = Depends(analyst_user)):
    result = await chat_service.answer_country(
        request.countryID, request.questionText, request.historyText, pillar_id=request.pillarID
    )
    return ChatResponse(success=True, message="Response fetched successfully", result=result)


@router.post("/country", response_model=ChatResponse)
async def ask_country(request: ChatCountryRequest, _: UserContext = Depends(analyst_user)):
    result = await chat_service.answer_country(
        request.countryID,
        request.questionText,
        request.historyText,
        request.faqid,
        request.pillarID,
    )
    return ChatResponse(success=True, message="Response fetched successfully", result=result)


@router.post("/global", response_model=ChatResponse)
async def ask_global(request: ChatGlobalRequest, _: UserContext = Depends(analyst_user)):
    result = await chat_service.answer_global(request.questionText, request.historyText, request.faqid)
    return ChatResponse(success=True, message="Response fetched successfully", result=result)


@router.post("/cross-comparision", response_model=ChatResponse)
async def ask_comparison(request: ChatCrossComparisionRequest, _: UserContext = Depends(analyst_user)):
    result = await chat_service.answer_comparison(
        request.questionText, request.countryIDs, request.historyText
    )
    return ChatResponse(success=True, message="Response fetched successfully", result=result)


@router.post("/executive-slides", response_model=ChatCountryExecutiveSlidesResponse)
async def ask_executive_slides(
    request: ChatCountryExecutiveSlidesRequest, _: UserContext = Depends(analyst_user)
):
    response = await chat_service.executive_slides(request.countryId)
    return ChatCountryExecutiveSlidesResponse(
        success=response["success"], message=response["message"], result=response["result"]
    )


@router.get("/emerging-trends-and-issues", response_model=ChatEmergingTrendsResponse)
async def get_emerging_trends(
    countryCount: int = Query(default=8, ge=1, le=250),
    queryVariant: Optional[int] = Query(default=None, ge=0),
    _: UserContext = Depends(analyst_user),
):
    response = await chat_service.emerging_trends(countryCount, queryVariant)
    if not response.get("success"):
        raise HTTPException(status_code=502, detail=response.get("message"))
    return ChatEmergingTrendsResponse(
        success=True, message=response["message"], result=response["result"]
    )


@router.get("/pillar-live-signals", response_model=ChatPillarLiveSignalsResponse)
async def get_pillar_live_signals(_: UserContext = Depends(analyst_user)):
    response = await chat_service.pillar_live_signals()
    if not response.get("success"):
        raise HTTPException(status_code=502, detail=response.get("message"))
    return ChatPillarLiveSignalsResponse(
        success=True, message=response["message"], result=response["result"]
    )


@router.post("/kpi-summary", response_model=KpiSummaryResponse)
async def summarize_kpi(request: KpiSummaryRequest, _: UserContext = Depends(analyst_user)):
    if not request.layerName or not request.layerCode:
        raise HTTPException(status_code=400, detail="layerName and layerCode are required")
    response = await chat_service.summarize_kpi(request.model_dump())
    result_data = response.get("result") or {}
    return KpiSummaryResponse(
        success=bool(response.get("success")),
        message=response.get("message"),
        result=KpiSummaryResult(**result_data) if result_data and "summary" in result_data else None,
    )
