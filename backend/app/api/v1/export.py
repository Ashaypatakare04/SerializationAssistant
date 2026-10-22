from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.adaptation import Episode
from backend.app.models.asset import Export
from backend.app.schemas.asset import JobResponse, ExportResponse
from backend.app.services.storage import storage_service
from backend.app.workers.job_runner import job_runner

from backend.app.core.security import get_current_user_id, verify_project_access

router = APIRouter(tags=["Export"])

@router.post("/episodes/{episode_id}/export-jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_episode_export(
    episode_id: str,
    require_all_approved: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = select(Episode).where(Episode.id == episode_id)
    res = await db.execute(stmt)
    episode = res.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found.")

    from backend.app.models.adaptation import AdaptationPlan
    plan_stmt = select(AdaptationPlan).where(AdaptationPlan.id == episode.adaptation_plan_id)
    plan_res = await db.execute(plan_stmt)
    plan = plan_res.scalar_one()

    await verify_project_access(plan.project_id, user_id, db)

    job = await job_runner.create_job(
        project_id=plan.project_id,
        job_type="episode_export",
        payload={
            "episode_id": episode_id,
            "require_all_approved": require_all_approved
        }
    )
    return job

@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = select(Export).where(Export.id == export_id)
    res = await db.execute(stmt)
    exp = res.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Export record not found.")

    await verify_project_access(exp.project_id, user_id, db)
    return exp

@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = select(Export).where(Export.id == export_id)
    res = await db.execute(stmt)
    exp = res.scalar_one_or_none()
    if not exp:
        raise HTTPException(status_code=404, detail="Export not found.")

    await verify_project_access(exp.project_id, user_id, db)

    abs_path = storage_service.get_absolute_path(exp.storage_key)
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Export file missing from storage.")

    return FileResponse(
        path=str(abs_path),
        filename=abs_path.name,
        media_type="application/zip"
    )

