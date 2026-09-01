from pydantic import BaseModel, Field
from typing import Any, Optional


class AnalysisResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None
    jobId: Optional[str] = None
    coalesced: bool = False


class MissingPillarQuestionRequest(BaseModel):
    countryID: int
    pillarID: Optional[int] = None
