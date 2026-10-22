from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.adaptation import Panel, Beat, Scene, Episode, AdaptationPlan
from backend.app.models.asset import Asset, AssetVersion
from backend.app.schemas.asset import GenerationJobCreate, EditJobCreate, JobResponse, AssetResponse
from backend.app.services.approval import approval_service
from backend.app.workers.job_runner import job_runner

from backend.app.core.security import get_current_user_id, verify_project_access

router = APIRouter(tags=["Generation"])

@router.post("/panels/{panel_id}/generation-jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_panel_generation(
    panel_id: str,
    data: GenerationJobCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = (
        select(Panel)
        .options(
            selectinload(Panel.beat)
            .selectinload(Beat.scene)
            .selectinload(Scene.episode)
            .selectinload(Episode.adaptation_plan)
        )
        .where(Panel.id == panel_id)
    )
    res = await db.execute(stmt)
    panel = res.scalar_one_or_none()
    if not panel:
        raise HTTPException(status_code=404, detail="Panel not found.")

    project_id = panel.beat.scene.episode.adaptation_plan.project_id
    await verify_project_access(project_id, user_id, db)

    # REQUIREMENT 2.5 & TEST 6: Enforce Approval Gate for Final Generation
    if data.stage == "final" and not panel.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval gate failure: Cannot generate final illustration for unapproved panel {panel.panel_number}."
        )

    job_type = "final_generation" if data.stage == "final" else "draft_generation"

    job = await job_runner.create_job(
        project_id=project_id,
        job_type=job_type,
        payload={
            "panel_id": panel_id,
            "panel_version": panel.version,
            "stage": data.stage,
            "prompt_override": data.prompt_override,
            "negative_prompt": data.negative_prompt,
            "provider_override": data.provider_override
        }
    )
    return job

@router.post("/assets/{asset_id}/edit-jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_asset_edit(
    asset_id: str,
    data: EditJobCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = select(Asset).where(Asset.id == asset_id)
    res = await db.execute(stmt)
    asset = res.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found.")

    await verify_project_access(asset.project_id, user_id, db)

    job = await job_runner.create_job(
        project_id=asset.project_id,
        job_type="panel_edit",
        payload={
            "asset_id": asset_id,
            "instruction": data.instruction,
            "target_region": data.target_region,
            "mask_storage_key": data.mask_storage_key
        }
    )
    return job


@router.get("/panels/{panel_id}/assets", response_model=List[AssetResponse])
async def list_panel_assets(
    panel_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Asset)
        .options(selectinload(Asset.versions))
        .where(Asset.panel_id == panel_id)
        .order_by(Asset.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
