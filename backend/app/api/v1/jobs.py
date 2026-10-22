from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.asset import Job
from backend.app.schemas.asset import JobResponse
from backend.app.workers.job_runner import job_runner

router = APIRouter(tags=["Jobs & Tasks"])

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job

@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    cancelled = await job_runner.cancel_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Job could not be cancelled or has already completed.")

    stmt = select(Job).where(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    return job

@router.get("/projects/{project_id}/jobs", response_model=List[JobResponse])
async def list_project_jobs(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Job)
        .where(Job.project_id == project_id)
        .order_by(Job.created_at.desc())
        .limit(50)
    )
    res = await db.execute(stmt)
    return res.scalars().all()
