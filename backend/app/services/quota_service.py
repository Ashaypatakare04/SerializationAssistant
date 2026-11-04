from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.models.asset import Job


class QuotaService:
    """Tracks and enforces project daily AI generation usage quotas to prevent runaway cloud costs."""

    async def get_usage_count(self, project_id: str, db: AsyncSession, hours: int = 24) -> int:
        since_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        threshold_utc = since_time.replace(tzinfo=None)
        
        stmt = (
            select(Job.created_at)
            .where(
                Job.project_id == project_id,
                Job.job_type.in_(["draft_generation", "final_generation", "panel_edit"])
            )
        )
        res = await db.execute(stmt)
        created_list = res.scalars().all()
        
        count = 0
        for created in created_list:
            if created:
                dt = created.replace(tzinfo=None) if created.tzinfo else created
                if dt >= threshold_utc:
                    count += 1
        return count

    async def check_generation_quota(
        self,
        project_id: str,
        db: AsyncSession,
        limit: Optional[int] = None
    ) -> int:
        """
        Enforces generation quota. Raises HTTP 429 if limit is exceeded.
        """
        max_jobs = limit or settings.MAX_DAILY_GENERATIONS_PER_PROJECT
        count = await self.get_usage_count(project_id, db, hours=24)
        if count >= max_jobs:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Daily generation quota exceeded for project {project_id} "
                    f"({count}/{max_jobs} jobs in last 24h). Quota resets continuously."
                )
            )
        return count


quota_service = QuotaService()
