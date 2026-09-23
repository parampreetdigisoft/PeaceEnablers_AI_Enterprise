from typing import Any, Optional

from pydantic import BaseModel, Field


class JobView(BaseModel):
    jobId: str
    coalescingKey: str
    resourceType: str
    status: str
    countryId: Optional[int] = None
    pillarId: Optional[int] = None
    questionId: Optional[int] = None
    attachedUserIds: list[str] = []
    attachedUserRoles: dict[str, list[str]] = Field(default_factory=dict)
    elapsedSeconds: float = 0
    provider: Optional[str] = None
    model: Optional[str] = None
    purpose: Optional[str] = None
    createdBy: Optional[str] = None
    createdByRoles: list[str] = Field(default_factory=list)
    attached: bool = False
    error: Optional[str] = None
    createdAt: Optional[str] = None
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    result: Any = None
