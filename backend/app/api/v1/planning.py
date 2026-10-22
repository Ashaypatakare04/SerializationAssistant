from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.project import Project
from backend.app.models.adaptation import AdaptationPlan, Episode, Scene, Beat, Panel, DialogueSegment
from backend.app.schemas.adaptation import AdaptationPlanResponse, EpisodeResponse
from backend.app.schemas.asset import JobResponse
from backend.app.workers.job_runner import job_runner

from backend.app.core.security import get_current_user_id, verify_project_access

router = APIRouter(tags=["Adaptation Planning"])

@router.post("/projects/{project_id}/adaptation-plans", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_adaptation_planning(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await verify_project_access(project_id, user_id, db)

    job = await job_runner.create_job(
        project_id=project_id,
        job_type="adaptation_plan",
        payload={}
    )
    return job

@router.get("/projects/{project_id}/adaptation-plans", response_model=List[AdaptationPlanResponse])
async def list_adaptation_plans(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await verify_project_access(project_id, user_id, db)
    stmt = (
        select(AdaptationPlan)
        .options(
            selectinload(AdaptationPlan.episodes)
            .selectinload(Episode.scenes)
            .selectinload(Scene.beats)
            .selectinload(Beat.panels)
            .selectinload(Panel.dialogues)
        )
        .where(AdaptationPlan.project_id == project_id)
        .order_by(AdaptationPlan.version.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()

@router.get("/episodes/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    episode_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = (
        select(Episode)
        .options(
            selectinload(Episode.adaptation_plan),
            selectinload(Episode.scenes)
            .selectinload(Scene.beats)
            .selectinload(Beat.panels)
            .selectinload(Panel.dialogues)
        )
        .where(Episode.id == episode_id)
    )
    res = await db.execute(stmt)
    episode = res.scalar_one_or_none()
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found.")

    if episode.adaptation_plan:
        await verify_project_access(episode.adaptation_plan.project_id, user_id, db)

    return episode

