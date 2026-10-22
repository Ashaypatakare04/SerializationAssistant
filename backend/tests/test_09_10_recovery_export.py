import pytest
import zipfile
import io
from httpx import AsyncClient
from sqlalchemy import select
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.asset import Job
from backend.app.workers.job_runner import job_runner
from backend.tests.conftest import wait_for_job

@pytest.mark.asyncio
async def test_09_job_recovery_after_restart(client: AsyncClient):
    # Create project and insert an orphaned 'running' job into DB
    res = await client.post("/api/v1/projects", json={"title": "Recovery Project"})
    project_id = res.json()["id"]

    async with AsyncSessionLocal() as session:
        orphan = Job(
            project_id=project_id,
            job_type="story_analysis",
            status="running",
            progress_percentage=45,
            stage_description="Executing when server suddenly stopped",
            payload={},
            retry_count=0,
            max_retries=3
        )
        session.add(orphan)
        await session.commit()
        orphan_id = orphan.id

    # Execute recovery routine (called on lifespan startup)
    await job_runner.recover_orphaned_jobs()

    # Verify job status was reset to queued with incremented retry count
    async with AsyncSessionLocal() as session:
        stmt = select(Job).where(Job.id == orphan_id)
        res = await session.execute(stmt)
        recovered = res.scalar_one()
        assert recovered.status == "queued"
        assert recovered.retry_count == 1
        assert "Recovered after server restart" in recovered.stage_description

@pytest.mark.asyncio
async def test_10_export_integrity(client: AsyncClient):
    res = await client.post("/api/v1/projects", json={"title": "Export Integrity Project"})
    project_id = res.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/documents",
        data={"raw_text": "Min-jun walked down the rain-slicked street. Soo-jin waited at the cafe.", "filename": "story.txt"}
    )
    analysis_job = await client.post(f"/api/v1/projects/{project_id}/analysis-jobs")
    await wait_for_job(client, analysis_job.json()["id"])

    plan_job = await client.post(f"/api/v1/projects/{project_id}/adaptation-plans")
    await wait_for_job(client, plan_job.json()["id"])

    plans_res = await client.get(f"/api/v1/projects/{project_id}/adaptation-plans")
    episode_id = plans_res.json()[0]["episodes"][0]["id"]
    storyboard_job = await client.post(f"/api/v1/episodes/{episode_id}/storyboard-jobs")
    await wait_for_job(client, storyboard_job.json()["id"])

    # Trigger export job
    export_job_res = await client.post(f"/api/v1/episodes/{episode_id}/export-jobs?require_all_approved=false")
    assert export_job_res.status_code == 202
    job_id = export_job_res.json()["id"]

    job_data = await wait_for_job(client, job_id)
    assert job_data["status"] == "completed"
    export_id = job_data["result_data"]["export_id"]

    # Verify Export Record
    exp_res = await client.get(f"/api/v1/exports/{export_id}")
    assert exp_res.status_code == 200
    exp = exp_res.json()
    assert exp["panel_count"] >= 1
    assert exp["total_height_px"] > 0
    assert "panels" in exp["manifest_data"]

    # Download ZIP and verify manifest inside
    dl_res = await client.get(f"/api/v1/exports/{export_id}/download")
    assert dl_res.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(dl_res.content))
    namelist = zf.namelist()
    assert "manifest.json" in namelist
    assert any("slices/" in n for n in namelist)
    assert any("panels/" in n for n in namelist)
