"""Admin observability: health, inflight jobs, country progress, cancel."""

from __future__ import annotations

from app.core.config import settings
from app.database.connection import sql_engine
from app.database.graph import graph_store
from app.vectorstores.factory import get_vector_store
from app.jobs.manager import job_manager
from app.jobs.registry import registry
from app.llm.router import llm_router
from app.models.job import Job
from app.services.evaluation_service import evaluation_service


class AdminService:
    def health(self) -> dict:
        sql_ok = sql_engine.test_connection()
        vector_ok = get_vector_store().healthy()
        return {
            "status": "healthy" if sql_ok else "degraded",
            "sql_server": {"connected": sql_ok, "database": settings.db_name},
            "vector_db": {
                "connected": vector_ok,
                "backend": settings.vector_db,
                "path": settings.vector_persist_path,
            },
            "graph_db": graph_store.healthy(),
            "llm": {
                "enabled_providers": llm_router.enabled_providers(),
                "single_llm_mode": llm_router._single_mode() is not None,
            },
        }

    async def inflight_jobs(self) -> list[dict]:
        jobs = await registry.list_inflight()
        return [self._job_view(j) for j in jobs]

    async def all_jobs(self) -> list[dict]:
        jobs = await registry.list_all()
        return [self._job_view(j) for j in jobs]

    async def country_status(self, country_id: int) -> dict:
        progress = evaluation_service.country_progress(country_id)
        jobs = [
            self._job_view(j)
            for j in await registry.list_all()
            if j.country_id == country_id
        ]
        return {**progress, "jobs": jobs}

    async def cancel(self, job_id: str) -> dict:
        job = await job_manager.cancel(job_id)
        return self._job_view(job)

    @staticmethod
    def _job_view(job: Job) -> dict:
        return {
            "jobId": job.id,
            "coalescingKey": job.coalescing_key,
            "resourceType": job.resource_type,
            "status": job.status.value,
            "countryId": job.country_id,
            "pillarId": job.pillar_id,
            "questionId": job.question_id,
            "attachedUserIds": job.attached_user_ids,
            "elapsedSeconds": round(job.elapsed_seconds, 2),
            "provider": job.provider,
            "model": job.model,
            "purpose": job.purpose,
            "createdBy": job.created_by,
            "attached": job.attached,
            "error": job.error,
            "createdAt": job.created_at.isoformat(),
            "startedAt": job.started_at.isoformat() if job.started_at else None,
            "completedAt": job.completed_at.isoformat() if job.completed_at else None,
        }


admin_service = AdminService()
