import pytest

from app.core.security import UserContext, reset_user_context, set_user_context
from app.jobs.manager import job_manager
from app.models.job import JobStatus


@pytest.mark.asyncio
async def test_duplicate_submit_attaches_and_runs_once():
    calls = {"n": 0}

    async def executor(job):
        calls["n"] += 1
        return {"ok": True}

    t1 = set_user_context(UserContext(user_id="user-a", roles=("Analyst",)))
    job1 = await job_manager.submit(
        coalescing_key="test:coalesce:unique-1",
        resource_type="evaluation_country",
        executor=executor,
        country_id=999,
        wait=False,
    )
    reset_user_context(t1)

    t2 = set_user_context(UserContext(user_id="user-b", roles=("Analyst",)))
    job2 = await job_manager.submit(
        coalescing_key="test:coalesce:unique-1",
        resource_type="evaluation_country",
        executor=executor,
        country_id=999,
        wait=False,
    )
    reset_user_context(t2)

    assert job1.id == job2.id
    assert job2.attached is True
    assert "user-a" in job2.attached_user_ids
    assert "user-b" in job2.attached_user_ids

    finished = await job_manager.wait_for(job1.id)
    assert finished.status == JobStatus.COMPLETED
    assert calls["n"] == 1
