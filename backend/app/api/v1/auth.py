from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    get_current_user,
    UserContext,
    verify_project_access
)
from backend.app.services.quota_service import quota_service

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])


class TokenRequest(BaseModel):
    user_id: str = Field(..., description="Unique user or account identifier")
    role: str = Field("creator", description="Studio role: creator, owner, admin, art_director, writer, storyboarder")
    expires_in: int = Field(86400, description="Token lifetime in seconds (default 24h)")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    expires_in: int


class UserProfileResponse(BaseModel):
    user_id: str
    role: str
    app_env: str


class ProjectQuotaResponse(BaseModel):
    project_id: str
    daily_used_generations: int
    daily_quota_limit: int
    remaining_generations: int


@router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def issue_token(data: TokenRequest):
    """Issues a cryptographically signed OAuth2 / Bearer JWT token with assigned studio role."""
    token = create_access_token(user_id=data.user_id, role=data.role, expires_in=data.expires_in)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=data.user_id,
        role=data.role,
        expires_in=data.expires_in
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(user_ctx: UserContext = Depends(get_current_user)):
    """Inspects currently authenticated user credentials and studio role."""
    return UserProfileResponse(
        user_id=user_ctx.user_id,
        role=user_ctx.role,
        app_env=settings.APP_ENV
    )


@router.get("/quota/{project_id}", response_model=ProjectQuotaResponse)
async def get_project_quota_status(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user_ctx: UserContext = Depends(get_current_user)
):
    """Returns current 24-hour generation quota utilization for a project."""
    await verify_project_access(project_id, user_ctx.user_id, db)
    used = await quota_service.get_usage_count(project_id, db, hours=24)
    limit = settings.MAX_DAILY_GENERATIONS_PER_PROJECT
    return ProjectQuotaResponse(
        project_id=project_id,
        daily_used_generations=used,
        daily_quota_limit=limit,
        remaining_generations=max(0, limit - used)
    )
