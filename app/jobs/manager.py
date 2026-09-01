"""
Job coalescing manager.

Guarantee: for a given coalescing key, at most one LLM-backed execution runs.
Concurrent HTTP requests attach to that job (same result, same LLM call).
This is what makes single-LLM mode safe under concurrent users.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from app.core.config import settings
from app.core.exceptions import JobCancelledError, NotFoundError
from app.core.security import current_user
from app.jobs.registry import registry
from app.models.job import IN_FLIGHT, Job, JobStatus
from app.repositories.job_repository import job_repository

logger = logging.getLogger(__name__)

Executor = Callable[[Job], Awaitable[Any]]


class JobManager:
    def __init__(self) -> None:
        self._start_lock = asyncio.Lock()

    def _cfg(self) -> dict:
        return settings.job_coalescing

    def _attach_statuses(self) -> set[JobStatus]:
        raw = self._cfg().get("attach_while_statuses") or ["queued", "running"]
        return {JobStatus(s) for s in raw}

    async def submit(
        self,
        *,
        coalescing_key: str,
        resource_type: str,
        executor: Executor,
        country_id: int | None = None,
        pillar_id: int | None = None,
        question_id: int | None = None,
        document_id: int | None = None,
        year: int | None = None,
        wait: bool = False,
        purpose: str | None = None,
    ) -> Job:
        """
        Get-or-create by coalescing_key. If an in-flight (or TTL-fresh completed)
        job exists, attach this user and return that job. Otherwise start one.
        """
        if not self._cfg().get("enabled", True):
            return await self._start_new(
                coalescing_key=coalescing_key,
                resource_type=resource_type,
                executor=executor,
                country_id=country_id,
                pillar_id=pillar_id,
                question_id=question_id,
                document_id=document_id,
                year=year,
                wait=wait,
                purpose=purpose,
            )

        user = current_user()
        async with self._start_lock:
            existing = await registry.get_by_key(coalescing_key)
            if existing and existing.status in self._attach_statuses():
                attached = await registry.attach_user(existing.id, user.user_id)
                assert attached is not None
                attached.attached = True
                logger.info(
                    "Coalesced request user=%s onto job=%s key=%s",
                    user.user_id,
                    attached.id,
                    coalescing_key,
                )
                job = attached
            elif existing and existing.status == JobStatus.COMPLETED and self._within_ttl(existing, "completed"):
                attached = await registry.attach_user(existing.id, user.user_id)
                assert attached is not None
                attached.attached = True
                logger.info("Reused completed job=%s key=%s (TTL)", attached.id, coalescing_key)
                job = attached
            else:
                job = await self._create_and_schedule(
                    coalescing_key=coalescing_key,
                    resource_type=resource_type,
                    executor=executor,
                    country_id=country_id,
                    pillar_id=pillar_id,
                    question_id=question_id,
                    document_id=document_id,
                    year=year,
                    purpose=purpose,
                    user_id=user.user_id,
                )

        if wait:
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return job
            return await self.wait_for(job.id)
        return job

    def _within_ttl(self, job: Job, kind: str) -> bool:
        ttl = int((self._cfg().get("ttl_seconds") or {}).get(kind, 0) or 0)
        if ttl <= 0 or job.completed_at is None:
            return False
        age = (datetime.now(timezone.utc) - job.completed_at).total_seconds()
        return age <= ttl

    async def _create_and_schedule(self, **kwargs) -> Job:
        user_id = kwargs.pop("user_id")
        executor: Executor = kwargs.pop("executor")
        job = Job(
            coalescing_key=kwargs["coalescing_key"],
            resource_type=kwargs["resource_type"],
            country_id=kwargs.get("country_id"),
            pillar_id=kwargs.get("pillar_id"),
            question_id=kwargs.get("question_id"),
            document_id=kwargs.get("document_id"),
            year=kwargs.get("year"),
            attached_user_ids=[user_id],
            created_by=user_id,
            purpose=kwargs.get("purpose"),
            status=JobStatus.QUEUED,
        )
        await registry.put(job)
        await job_repository.save(job)
        asyncio.create_task(self._run(job.id, executor), name=f"job-{job.id}")
        return job.model_copy(deep=True)

    async def _start_new(self, *, wait: bool, executor: Executor, **kwargs) -> Job:
        user = current_user()
        job = await self._create_and_schedule(executor=executor, user_id=user.user_id, **kwargs)
        if wait:
            return await self.wait_for(job.id)
        return job

    async def _run(self, job_id: str, executor: Executor) -> None:
        job = await registry.get(job_id)
        if job is None:
            return
        if job.status == JobStatus.CANCELLED:
            return
        now = datetime.now(timezone.utc)
        await registry.update(job_id, status=JobStatus.RUNNING, started_at=now)
        try:
            live = await registry.get(job_id)
            assert live is not None
            if live.status == JobStatus.CANCELLED:
                raise JobCancelledError(job_id)
            result = await executor(live)
            completed = datetime.now(timezone.utc)
            updated = await registry.update(
                job_id,
                status=JobStatus.COMPLETED,
                completed_at=completed,
                result=result,
                error=None,
            )
            if updated:
                await job_repository.save(updated)
                await registry.resolve_waiters(job_id, updated)
        except JobCancelledError:
            updated = await registry.get(job_id)
            if updated:
                await job_repository.save(updated)
                await registry.fail_waiters(job_id, JobCancelledError(job_id))
        except Exception as exc:
            logger.exception("Job %s failed: %s", job_id, exc)
            completed = datetime.now(timezone.utc)
            updated = await registry.update(
                job_id,
                status=JobStatus.FAILED,
                completed_at=completed,
                error=str(exc),
            )
            if updated:
                await job_repository.save(updated)
                await registry.fail_waiters(job_id, exc)

    async def wait_for(self, job_id: str) -> Job:
        job = await registry.get(job_id)
        if job is None:
            raise NotFoundError(f"Job {job_id} not found")
        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            if job.status == JobStatus.FAILED:
                raise RuntimeError(job.error or "Job failed")
            if job.status == JobStatus.CANCELLED:
                raise JobCancelledError(job_id)
            return job
        fut = await registry.add_waiter(job_id)
        return await fut

    async def cancel(self, job_id: str) -> Job:
        job = await registry.get(job_id)
        if job is None:
            raise NotFoundError(f"Job {job_id} not found")
        if job.status not in IN_FLIGHT:
            raise NotFoundError(f"Job {job_id} is not queued or running")
        now = datetime.now(timezone.utc)
        updated = await registry.update(
            job_id,
            status=JobStatus.CANCELLED,
            completed_at=now,
            error="Cancelled by admin",
        )
        assert updated is not None
        await job_repository.save(updated)
        await registry.fail_waiters(job_id, JobCancelledError(job_id))
        return updated

    async def record_llm(self, job_id: str, provider: str, model: str) -> None:
        await registry.update(job_id, provider=provider, model=model)


job_manager = JobManager()
