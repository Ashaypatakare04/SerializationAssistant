from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.project import Project
from backend.app.models.style import ReferenceAsset, StyleProfile, StyleProfileVersion
from backend.app.providers.factory import provider_factory

class StyleAnalysisService:
    @classmethod
    async def run_style_analysis(
        cls,
        db: AsyncSession,
        project_id: str
    ) -> StyleProfile:
        # Load reference assets for project
        stmt = select(ReferenceAsset).where(
            ReferenceAsset.project_id == project_id,
            ReferenceAsset.is_active == True
        )
        res = await db.execute(stmt)
        refs = res.scalars().all()
        if not refs:
            raise ValueError(f"Cannot perform style analysis: No active reference images uploaded for project {project_id}.")

        ref_data = [
            {
                "id": r.id,
                "filename": r.filename,
                "role": r.role,
                "label": r.label,
                "description": r.description or ""
            }
            for r in refs
        ]

        llm = provider_factory.get_llm_provider()
        profile_data = await llm.analyze_style(ref_data)

        # Check existing style profile
        stmt = select(StyleProfile).where(StyleProfile.project_id == project_id)
        res = await db.execute(stmt)
        style_profile = res.scalar_one_or_none()

        if not style_profile:
            style_profile = StyleProfile(
                project_id=project_id,
                current_version=1,
                status="draft"
            )
            db.add(style_profile)
            await db.flush()
            version_number = 1
        else:
            style_profile.current_version += 1
            version_number = style_profile.current_version

        version_obj = StyleProfileVersion(
            style_profile_id=style_profile.id,
            version_number=version_number,
            linework_and_contours=profile_data.get("linework_and_contours", ""),
            anatomy_and_proportions=profile_data.get("anatomy_and_proportions", ""),
            facial_features_and_expressions=profile_data.get("facial_features_and_expressions", ""),
            palette_and_colors=profile_data.get("palette_and_colors", []),
            color_relationships=profile_data.get("color_relationships", ""),
            shading_and_lighting=profile_data.get("shading_and_lighting", ""),
            texture_and_rendering=profile_data.get("texture_and_rendering", ""),
            background_treatment=profile_data.get("background_treatment", ""),
            composition_conventions=profile_data.get("composition_conventions", ""),
            degree_of_stylization=profile_data.get("degree_of_stylization", "high"),
            reference_isolation_notes=profile_data.get("reference_isolation_notes", "Style-only extraction. No reference characters or story events imported."),
            uncertainties=profile_data.get("uncertainties", []),
            reference_asset_ids=[r.id for r in refs],
            is_approved=False
        )
        db.add(version_obj)

        proj_stmt = select(Project).where(Project.id == project_id)
        proj_res = await db.execute(proj_stmt)
        proj = proj_res.scalar_one_or_none()
        if proj and proj.current_stage == "story_analysis":
            proj.current_stage = "style_analysis"

        await db.commit()
        await db.refresh(style_profile)
        return style_profile

style_analysis_service = StyleAnalysisService()
