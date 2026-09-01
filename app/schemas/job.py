from typing import Any, Optional

from pydantic import BaseModel


class JobView(BaseModel):
    jobId: str
    coalescingKey: str
    resourceType: str
    status: str
    countryId: Optional[int] = None
    pillarId: Optional[int] = None
    questionId: Optional[int] = None
    attachedUserIds: list[str] = []
    elapsedSeconds: float = 0
    provider: Optional[str] = None
    model: Optional[str] = None
    purpose: Optional[str] = None
    createdBy: Optional[str] = None
    attached: bool = False
    error: Optional[str] = None
    createdAt: Optional[str] = None
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    result: Any = None
