from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.core.security import get_current_user_id
from backend.app.models.project import Project, User, ProjectMember
from backend.app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    # Ensure default user exists
    user_stmt = select(User).where(User.id == user_id)
    u_res = await db.execute(user_stmt)
    user = u_res.scalar_one_or_none()
    if not user:
        user = User(id=user_id, email=f"{user_id}@studio.local", name="Creator")
        db.add(user)
        await db.flush()

    project = Project(
        title=data.title,
        description=data.description,
        target_format=data.target_format,
        configuration=data.configuration,
        owner_id=user.id,
        current_stage="source_intake",
        status="active"
    )
    db.add(project)
    await db.flush()

    # Add owner member
    member = ProjectMember(project_id=project.id, user_id=user.id, role="owner")
    db.add(member)

    await db.commit()
    await db.refresh(project)
    return project

@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    stmt = (
        select(Project)
        .options(selectinload(Project.documents))
        .where(Project.owner_id == user_id)
        .order_by(Project.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()

from backend.app.core.security import get_current_user_id, verify_project_access

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await verify_project_access(project_id, user_id, db)
    stmt = (
        select(Project)
        .options(selectinload(Project.documents))
        .where(Project.id == project_id)
    )
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    project = await verify_project_access(project_id, user_id, db, require_owner=False)

    for field, val in data.model_dump(exclude_unset=True).items():
        setattr(project, field, val)

    await db.commit()
    await db.refresh(project)
    return project

