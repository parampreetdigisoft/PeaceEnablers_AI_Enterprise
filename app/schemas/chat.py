from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    countryID: int
    questionText: str
    historyText: Optional[str] = None
    pillarID: Optional[int] = None


class ChatCountryRequest(BaseModel):
    countryID: int
    questionText: str
    historyText: Optional[str] = None
    faqid: Optional[int] = None
    pillarID: Optional[int] = None


class ChatGlobalRequest(BaseModel):
    questionText: str
    historyText: Optional[str] = None
    faqid: Optional[int] = None


class ChatCrossComparisionRequest(BaseModel):
    questionText: str
    countryIDs: list[int]
    historyText: Optional[str] = None
    faqid: Optional[int] = None


class ChatResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    result: Optional[str] = None


class ChatCountryExecutiveSlidesRequest(BaseModel):
    countryId: int


class ChatCountryExecutiveSlidesResponse(BaseModel):
    success: bool
    message: str
    result: Any


class KpiInterpretationBand(BaseModel):
    minRange: Optional[float] = None
    maxRange: Optional[float] = None
    condition: Optional[str] = None
    descriptor: Optional[str] = None
    strategicAction: Optional[str] = None


class KpiSummaryRequest(BaseModel):
    countryName: Optional[str] = None
    layerName: str
    layerCode: str
    purpose: Optional[str] = None
    manualScore: Optional[float] = None
    aiScore: Optional[float] = None
    manualCondition: Optional[str] = None
    aiCondition: Optional[str] = None
    interpretationBands: List[KpiInterpretationBand] = Field(default_factory=list)
    categoryDetails: Optional[str] = None


class KpiSummaryResult(BaseModel):
    summary: str
    scoreInterpretation: Optional[str] = None
    keyTakeaways: List[str] = Field(default_factory=list)
    outlook: Optional[str] = None


class KpiSummaryResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    result: Optional[KpiSummaryResult] = None


class ChatEmergingTrendsResponse(BaseModel):
    success: bool
    message: str
    result: Any


class ChatPillarLiveSignalsResponse(BaseModel):
    success: bool
    message: str
    result: Any
