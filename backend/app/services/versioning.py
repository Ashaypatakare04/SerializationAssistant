from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.asset import Asset, AssetVersion, AssetDependency
from backend.app.models.adaptation import Panel

class VersioningService:
    @classmethod
    async def record_dependencies(
        cls,
        db: AsyncSession,
        asset_version_id: str,
        panel_id: str,
        panel_version: int,
        style_profile_id: str,
        style_version: int,
        character_refs: List[Dict[str, Any]]
    ):
        # 1. Panel spec dependency
        db.add(AssetDependency(
            asset_version_id=asset_version_id,
            dependency_type="panel_spec",
            dependency_id=panel_id,
            dependency_version=panel_version,
            is_stale=False
        ))
        # 2. Style profile dependency
        db.add(AssetDependency(
            asset_version_id=asset_version_id,
            dependency_type="style_profile",
            dependency_id=style_profile_id,
            dependency_version=style_version,
            is_stale=False
        ))
        # 3. Character refs
        for ref in character_refs:
            ref_id = ref.get("id") or ref.get("reference_asset_id")
            if ref_id:
                db.add(AssetDependency(
                    asset_version_id=asset_version_id,
                    dependency_type="character_ref",
                    dependency_id=ref_id,
                    dependency_version=ref.get("version", 1),
                    is_stale=False
                ))
        await db.flush()

    @classmethod
    async def check_stale_job_overwrite_guard(
        cls,
        db: AsyncSession,
        panel_id: str,
        incoming_target_panel_version: int
    ) -> bool:
        """
        Ensures a stale background generation job cannot overwrite or activate 
        if the panel has since been updated or if an approved newer asset exists.
        Returns True if safe to apply, False if stale.
        """
        stmt = select(Panel).where(Panel.id == panel_id)
        res = await db.execute(stmt)
        panel = res.scalar_one_or_none()
        if not panel:
            return False

        # If panel version has advanced beyond incoming target, it's stale
        if panel.version > incoming_target_panel_version:
            return False

        # If current active asset is already approved, do not silently overwrite
        if panel.active_asset_id:
            asset_stmt = select(Asset).where(Asset.id == panel.active_asset_id)
            asset_res = await db.execute(asset_stmt)
            active_asset = asset_res.scalar_one_or_none()
            if active_asset and active_asset.status == "approved":
                return False

        return True

    @classmethod
    async def get_stale_asset_versions(cls, db: AsyncSession, project_id: str) -> List[str]:
        """Finds all asset versions whose dependencies are outdated."""
        stmt = select(AssetDependency).where(AssetDependency.is_stale == True)
        res = await db.execute(stmt)
        deps = res.scalars().all()
        return [d.asset_version_id for d in deps]

versioning_service = VersioningService()
