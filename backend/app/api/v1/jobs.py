import json
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db, AsyncSessionLocal
from backend.app.models.asset import Job
from backend.app.schemas.asset import JobResponse
from backend.app.workers.job_runner import job_runner

from backend.app.core.security import get_current_user_id, verify_project_access

router = APIRouter(tags=["Jobs & Tasks"])

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    await verify_project_access(job.project_id, user_id, db)
    return job

@router.get("/jobs/{job_id}/stream")
async def stream_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    await verify_project_access(job.project_id, user_id, db)

    async def event_generator():
        last_status = None
        last_progress = None
        while True:
            async with AsyncSessionLocal() as session:
                j_stmt = select(Job).where(Job.id == job_id)
                j_res = await session.execute(j_stmt)
                current_job = j_res.scalar_one_or_none()
                if not current_job:
                    yield f"event: error\ndata: {json.dumps({'error': 'Job disappeared'})}\n\n"
                    break

                job_data = {
                    "id": current_job.id,
                    "project_id": current_job.project_id,
                    "job_type": current_job.job_type,
                    "status": current_job.status,
                    "stage_description": current_job.stage_description,
                    "progress_percentage": current_job.progress_percentage,
                    "error_message": current_job.error_message,
                    "result_data": current_job.result_data
                }

                if (
                    current_job.status != last_status
                    or current_job.progress_percentage != last_progress
                    or current_job.status in ("completed", "failed", "cancelled")
                ):
                    last_status = current_job.status
                    last_progress = current_job.progress_percentage
                    yield f"event: update\ndata: {json.dumps(job_data)}\n\n"

                if current_job.status in ("completed", "failed", "cancelled"):
                    break

            await asyncio.sleep(0.4)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    await verify_project_access(job.project_id, user_id, db)

    cancelled = await job_runner.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Job could not be cancelled or has already completed.")

    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    return job

@router.get("/projects/{project_id}/jobs", response_model=List[JobResponse])
async def list_project_jobs(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await verify_project_access(project_id, user_id, db)
    stmt = (
        select(Job)
        .where(Job.project_id == project_id)
        .order_by(Job.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)
    return res.scalars().all()

