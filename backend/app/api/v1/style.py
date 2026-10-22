from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.project import Project
from backend.app.models.style import StyleProfile, StyleProfileVersion
from backend.app.schemas.style import StyleProfileResponse, StyleProfileVersionResponse, StyleProfileUpdate
from backend.app.schemas.asset import JobResponse
from backend.app.workers.job_runner import job_runner

router = APIRouter(tags=["Style Analysis"])

@router.post("/projects/{project_id}/style-analysis-jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_style_analysis(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found.")

    job = await job_runner.create_job(
        project_id=project_id,
        job_type="style_analysis",
        payload={}
    )
    return job

@router.get("/projects/{project_id}/style-profile", response_model=StyleProfileResponse)
async def get_style_profile(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(StyleProfile)
        .options(selectinload(StyleProfile.versions))
        .where(StyleProfile.project_id == project_id)
    )
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="No style profile found. Please run style analysis first.")
    return profile

@router.patch("/style-profiles/{profile_id}/versions/{version_number}", response_model=StyleProfileVersionResponse)
async def update_style_profile_version(
    profile_id: str,
    version_number: int,
    data: StyleProfileUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(StyleProfileVersion).where(
        StyleProfileVersion.style_profile_id == profile_id,
        StyleProfileVersion.version_number == version_number
    )
    res = await db.execute(stmt)
    ver = res.scalar_one_or_none()
    if not ver:
        raise HTTPException(status_code=404, detail="Style profile version not found.")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(ver, field, val)

    await db.commit()
    await db.refresh(ver)
    return ver
