import asyncio
import pytest
from sqlalchemy import select
from backend.app.core.config import settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.asset import Job
from backend.app.workers.standalone_worker import StandaloneWorkerRunner


@pytest.mark.asyncio
async def test_standalone_worker_claim_and_execute():
    # 1. Create a dummy test job in queued status
    async with AsyncSessionLocal() as session:
        job = Job(
            project_id="test_worker_proj",
            job_type="test_mock",
            status="queued",
            progress_percentage=0,
            stage_description="Queued test job",
            payload={"action": "test"},
            result_data={},
            retry_count=0,
            max_retries=3,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        test_job_id = job.id

    worker = StandaloneWorkerRunner()
    
    # Test claiming
    claimed = await worker.claim_queued_jobs(limit=2)
    assert test_job_id in claimed

    async with AsyncSessionLocal() as session:
        stmt = select(Job).where(Job.id == test_job_id)
        res = await session.execute(stmt)
        claimed_job = res.scalar_one()
        assert claimed_job.status == "running"
        assert "claimed by decoupled worker" in claimed_job.stage_description.lower()

    # Clean up test job
    async with AsyncSessionLocal() as session:
        stmt = select(Job).where(Job.id == test_job_id)
        res = await session.execute(stmt)
        claimed_job = res.scalar_one()
        claimed_job.status = "completed"
        await session.commit()


@pytest.mark.asyncio
async def test_standalone_worker_stop_signal():
    worker = StandaloneWorkerRunner()
    assert worker.is_running is True
    assert not worker.stop_event.is_set()

    worker.request_stop("SIGINT")
    assert worker.is_running is False
    assert worker.stop_event.is_set()
