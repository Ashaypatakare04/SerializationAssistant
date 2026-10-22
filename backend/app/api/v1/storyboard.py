from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.adaptation import Episode, Panel, DialogueSegment
from backend.app.schemas.adaptation import PanelResponse, PanelUpdate, DialogueSegmentCreate, DialogueSegmentResponse
from backend.app.schemas.asset import JobResponse
from backend.app.services.storyboard import storyboard_service
from backend.app.workers.job_runner import job_runner

from backend.app.core.security import get_current_user_id, verify_project_access

router = APIRouter(tags=["Storyboard"])

@router.post("/episodes/{episode_id}/storyboard-jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_storyboard_generation(
    episode_id: str,
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
        job_type="storyboard_gen",
        payload={"episode_id": episode_id}
    )
    return job


@router.patch("/panels/{panel_id}", response_model=PanelResponse)
async def update_panel(
    panel_id: str,
    data: PanelUpdate,
    db: AsyncSession = Depends(get_db)
):
    update_dict = data.model_dump(exclude_unset=True)
    try:
        panel = await storyboard_service.update_panel(db, panel_id, update_dict)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Re-fetch with dialogues
    stmt = select(Panel).options(selectinload(Panel.dialogues)).where(Panel.id == panel_id)
    res = await db.execute(stmt)
    return res.scalar_one()

@router.post("/panels/{panel_id}/dialogues", response_model=DialogueSegmentResponse, status_code=status.HTTP_201_CREATED)
async def add_dialogue_to_panel(
    panel_id: str,
    data: DialogueSegmentCreate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Panel).where(Panel.id == panel_id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Panel not found.")

    dialogue = DialogueSegment(
        panel_id=panel_id,
        segment_type=data.segment_type,
        speaker_character_id=data.speaker_character_id,
        speaker_name=data.speaker_name,
        text_content=data.text_content,
        order_in_panel=data.order_in_panel,
        position_hint=data.position_hint
    )
    db.add(dialogue)
    await db.commit()
    await db.refresh(dialogue)
    return dialogue
