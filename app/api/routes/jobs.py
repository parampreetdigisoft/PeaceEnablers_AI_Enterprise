"""Caller-facing job status (analysts see jobs they are attached to)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import analyst_user
from app.core.security import UserContext
from app.jobs.registry import registry
from app.schemas.job import JobView
from app.services.admin_service import admin_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(analyst_user)])


@router.get("/{job_id}", response_model=JobView)
async def get_job(job_id: str, user: UserContext = Depends(analyst_user)):
    job = await registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not user.has_role("Admin") and user.user_id not in job.attached_user_ids:
        raise HTTPException(status_code=403, detail="Not attached to this job")
    return JobView(**admin_service._job_view(job))
