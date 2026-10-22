from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.models.project import Project
from backend.app.models.bible import StoryBible, Character
from backend.app.schemas.bible import StoryBibleResponse, StoryBibleUpdate
from backend.app.schemas.asset import JobResponse
from backend.app.workers.job_runner import job_runner

router = APIRouter(tags=["Story Analysis"])

@router.post("/projects/{project_id}/analysis-jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_story_analysis(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found.")

    job = await job_runner.create_job(
        project_id=project_id,
        job_type="story_analysis",
        payload={}
    )
    return job

@router.get("/projects/{project_id}/story-bible", response_model=StoryBibleResponse)
async def get_story_bible(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(StoryBible)
        .options(
            selectinload(StoryBible.characters).selectinload(Character.versions),
            selectinload(StoryBible.events),
            selectinload(StoryBible.continuity_facts),
            selectinload(StoryBible.relationships)
        )
        .where(StoryBible.project_id == project_id)
        .order_by(StoryBible.version.desc())
    )
    res = await db.execute(stmt)
    bible = res.scalars().first()
    if not bible:
        raise HTTPException(status_code=404, detail="No story bible found. Please run story analysis first.")
    return bible

@router.patch("/story-bibles/{bible_id}", response_model=StoryBibleResponse)
async def update_story_bible(
    bible_id: str,
    data: StoryBibleUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(StoryBible)
        .options(
            selectinload(StoryBible.characters).selectinload(Character.versions),
            selectinload(StoryBible.events),
            selectinload(StoryBible.continuity_facts),
            selectinload(StoryBible.relationships)
        )
        .where(StoryBible.id == bible_id)
    )
    res = await db.execute(stmt)
    bible = res.scalar_one_or_none()
    if not bible:
        raise HTTPException(status_code=404, detail="Story bible not found.")

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(bible, field, val)

    await db.commit()
    await db.refresh(bible)
    return bible
