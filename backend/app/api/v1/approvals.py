from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.core.security import get_current_user_id
from backend.app.models.asset import Approval
from backend.app.schemas.asset import ApprovalCreate, ApprovalResponse
from backend.app.services.approval import approval_service

router = APIRouter(tags=["Approvals"])

@router.post("/artifacts/{artifact_id}/approvals", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
async def record_approval(
    artifact_id: str,
    data: ApprovalCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    try:
        approval = await approval_service.record_approval(
            db=db,
            project_id=data.artifact_id if data.artifact_type == "project" else "default",
            artifact_type=data.artifact_type,
            artifact_id=artifact_id,
            artifact_version=data.artifact_version,
            approved_by=data.approved_by or user_id,
            comments=data.comments
        )
        return approval
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

from backend.app.core.security import get_current_user_id, verify_project_access

@router.get("/projects/{project_id}/approvals", response_model=List[ApprovalResponse])
async def list_project_approvals(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    await verify_project_access(project_id, user_id, db)
    stmt = (
        select(Approval)
        .where(Approval.project_id == project_id)
        .order_by(Approval.created_at.desc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()

