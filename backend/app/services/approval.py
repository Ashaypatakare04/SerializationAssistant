from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.asset import Approval
from backend.app.models.bible import StoryBible
from backend.app.models.style import StyleProfile, StyleProfileVersion
from backend.app.models.adaptation import AdaptationPlan, Panel, Episode
from backend.app.models.asset import Asset, AssetVersion

class ApprovalService:
    @classmethod
    async def record_approval(
        cls,
        db: AsyncSession,
        project_id: str,
        artifact_type: str,
        artifact_id: str,
        artifact_version: int,
        approved_by: str,
        comments: Optional[str] = None
    ) -> Approval:
        if not approved_by or any(term in approved_by.lower() for term in ("ai", "system", "auto", "mock", "llm", "agent", "bot", "model")):
            raise ValueError("AI or automated systems cannot approve their own work. Explicit creator approval is required.")

        # Validate target artifact exists and matches requested version
        if artifact_type == "story_bible":
            stmt = select(StoryBible).where(StoryBible.id == artifact_id, StoryBible.version == artifact_version)
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                raise ValueError(f"StoryBible {artifact_id} v{artifact_version} not found.")
            obj.status = "approved"

        elif artifact_type == "style_profile":
            stmt = select(StyleProfileVersion).where(
                StyleProfileVersion.style_profile_id == artifact_id,
                StyleProfileVersion.version_number == artifact_version
            )
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                raise ValueError(f"StyleProfileVersion {artifact_id} v{artifact_version} not found.")
            obj.is_approved = True
            obj.approved_by = approved_by

        elif artifact_type == "adaptation_plan":
            stmt = select(AdaptationPlan).where(AdaptationPlan.id == artifact_id, AdaptationPlan.version == artifact_version)
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                raise ValueError(f"AdaptationPlan {artifact_id} v{artifact_version} not found.")
            obj.is_approved = True
            obj.status = "approved"
            obj.approved_by = approved_by

        elif artifact_type == "panel":
            stmt = select(Panel).where(Panel.id == artifact_id, Panel.version == artifact_version)
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                raise ValueError(f"Panel {artifact_id} v{artifact_version} not found.")
            obj.is_approved = True
            obj.approved_by = approved_by

        elif artifact_type == "asset_version":
            stmt = select(AssetVersion).where(AssetVersion.id == artifact_id, AssetVersion.version_number == artifact_version)
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                raise ValueError(f"AssetVersion {artifact_id} v{artifact_version} not found.")
            obj.is_approved = True

        elif artifact_type == "final_episode":
            stmt = select(Episode).where(Episode.id == artifact_id)
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none()
            if not obj:
                raise ValueError(f"Episode {artifact_id} not found.")
            obj.status = "completed"

        else:
            raise ValueError(f"Unsupported artifact type for approval: {artifact_type}")

        approval = Approval(
            project_id=project_id,
            artifact_type=artifact_type,
            artifact_id=artifact_id,
            artifact_version=artifact_version,
            approved_by=approved_by,
            comments=comments
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return approval

    @classmethod
    async def verify_panel_approved(cls, db: AsyncSession, panel_id: str) -> bool:
        stmt = select(Panel).where(Panel.id == panel_id)
        res = await db.execute(stmt)
        panel = res.scalar_one_or_none()
        return bool(panel and panel.is_approved)

approval_service = ApprovalService()
