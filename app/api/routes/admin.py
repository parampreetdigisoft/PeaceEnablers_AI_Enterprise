"""Admin-only observability. Requires X-User-Roles: Admin."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import admin_user
from app.core.security import UserContext
from app.schemas.admin import CancelResponse, HealthResponse
from app.services.admin_service import admin_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_user)])


@router.get("/health", response_model=HealthResponse)
async def admin_health(_: UserContext = Depends(admin_user)):
    return admin_service.health()


@router.get("/jobs")
async def list_jobs(_: UserContext = Depends(admin_user)):
    return {"jobs": await admin_service.inflight_jobs()}


@router.get("/jobs/all")
async def list_all_jobs(_: UserContext = Depends(admin_user)):
    return {"jobs": await admin_service.all_jobs()}


@router.get("/countries/{country_id}/status")
async def country_status(country_id: int, _: UserContext = Depends(admin_user)):
    return await admin_service.country_status(country_id)


@router.post("/jobs/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(job_id: str, _: UserContext = Depends(admin_user)):
    job = await admin_service.cancel(job_id)
    return CancelResponse(success=True, message="Job cancelled", job=job)
