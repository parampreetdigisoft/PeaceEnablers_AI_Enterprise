"""In-memory live job index. Admin list/cancel hits this, not SQL, so it stays fast."""

from __future__ import annotations

import asyncio
from collections import defaultdict

from app.models.job import IN_FLIGHT, Job, JobStatus


class JobRegistry:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_id: dict[str, Job] = {}
        self._by_key: dict[str, str] = {}  # coalescing_key → job_id (in-flight or TTL-eligible)
        self._waiters: dict[str, list[asyncio.Future]] = defaultdict(list)

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            job = self._by_id.get(job_id)
            return job.model_copy(deep=True) if job else None

    async def get_by_key(self, key: str) -> Job | None:
        async with self._lock:
            job_id = self._by_key.get(key)
            if not job_id:
                return None
            job = self._by_id.get(job_id)
            return job.model_copy(deep=True) if job else None

    async def list_inflight(self) -> list[Job]:
        async with self._lock:
            return [
                j.model_copy(deep=True)
                for j in self._by_id.values()
                if j.status in IN_FLIGHT
            ]

    async def list_all(self) -> list[Job]:
        async with self._lock:
            return [j.model_copy(deep=True) for j in self._by_id.values()]

    async def put(self, job: Job) -> Job:
        async with self._lock:
            self._by_id[job.id] = job
            if job.status in IN_FLIGHT:
                self._by_key[job.coalescing_key] = job.id
            return job.model_copy(deep=True)

    async def attach_user(self, job_id: str, user_id: str) -> Job | None:
        async with self._lock:
            job = self._by_id.get(job_id)
            if job is None:
                return None
            if user_id not in job.attached_user_ids:
                job.attached_user_ids.append(user_id)
            return job.model_copy(deep=True)

    async def update(self, job_id: str, **fields) -> Job | None:
        async with self._lock:
            job = self._by_id.get(job_id)
            if job is None:
                return None
            for key, value in fields.items():
                setattr(job, key, value)
            if job.status not in IN_FLIGHT and self._by_key.get(job.coalescing_key) == job.id:
                # keep key mapping so TTL reuse can find it; manager decides eviction
                pass
            return job.model_copy(deep=True)

    async def drop_key(self, key: str) -> None:
        async with self._lock:
            self._by_key.pop(key, None)

    async def add_waiter(self, job_id: str) -> asyncio.Future:
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        async with self._lock:
            self._waiters[job_id].append(fut)
        return fut

    async def resolve_waiters(self, job_id: str, job: Job) -> None:
        async with self._lock:
            waiters = self._waiters.pop(job_id, [])
        for fut in waiters:
            if not fut.done():
                fut.set_result(job.model_copy(deep=True))

    async def fail_waiters(self, job_id: str, exc: BaseException) -> None:
        async with self._lock:
            waiters = self._waiters.pop(job_id, [])
        for fut in waiters:
            if not fut.done():
                fut.set_exception(exc)


registry = JobRegistry()
