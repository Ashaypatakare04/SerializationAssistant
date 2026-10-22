import asyncio
import traceback
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import AsyncSessionLocal
from backend.app.models.asset import Job, Asset, AssetVersion, GenerationRun
from backend.app.models.adaptation import Panel
from backend.app.models.style import StyleProfileVersion, ReferenceAsset
from backend.app.services.story_analysis import story_analysis_service
from backend.app.services.style_analysis import style_analysis_service
from backend.app.services.serialization import serialization_service
from backend.app.services.storyboard import storyboard_service
from backend.app.services.storage import storage_service
from backend.app.services.versioning import versioning_service
from backend.app.export.webtoon_exporter import webtoon_exporter
from backend.app.providers.factory import provider_factory

class JobRunner:
    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._is_active = True

    async def create_job(
        self,
        project_id: str,
        job_type: str,
        payload: Dict[str, Any]
    ) -> Job:
        async with AsyncSessionLocal() as session:
            job = Job(
                project_id=project_id,
                job_type=job_type,
                status="queued",
                progress_percentage=0,
                stage_description="Job queued in persistent database queue",
                payload=payload,
                result_data={},
                retry_count=0,
                max_retries=3
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        # Schedule execution as background async task
        task = asyncio.create_task(self.execute_job(job_id))
        self._running_tasks[job_id] = task
        return job

    async def cancel_job(self, job_id: str) -> bool:
        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
            del self._running_tasks[job_id]

        async with AsyncSessionLocal() as session:
            stmt = select(Job).where(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if job and job.status in ("queued", "running"):
                job.status = "cancelled"
                job.stage_description = "Job was cancelled by creator."
                await session.commit()
                return True
        return False

    async def recover_orphaned_jobs(self):
        """
        On application restart, inspect the database for jobs left in 'running' state
        and reset them to retry or fail gracefully without data corruption.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(Job).where(Job.status == "running")
            res = await session.execute(stmt)
            orphans = res.scalars().all()
            for job in orphans:
                if job.retry_count < job.max_retries:
                    job.status = "queued"
                    job.retry_count += 1
                    job.stage_description = f"Recovered after server restart. Retry {job.retry_count}/{job.max_retries}"
                    logger.info(f"Recovered orphaned job {job.id} for retry.")
                else:
                    job.status = "failed"
                    job.error_message = "Job failed: interrupted by server shutdown and exceeded maximum retries."
            await session.commit()

    async def execute_job(self, job_id: str):
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(Job).where(Job.id == job_id)
                res = await session.execute(stmt)
                job = res.scalar_one_or_none()
                if not job or job.status == "cancelled":
                    return

                job.status = "running"
                job.progress_percentage = 10
                job.stage_description = "Initializing execution..."
                await session.commit()

                # Dispatch according to job type
                result = await self._dispatch(session, job)
                
                job.status = "completed"
                job.progress_percentage = 100
                job.stage_description = "Completed successfully."
                job.result_data = result or {}
                await session.commit()

        except asyncio.CancelledError:
            logger.warning(f"Job {job_id} cancelled.")
            async with AsyncSessionLocal() as session:
                stmt = select(Job).where(Job.id == job_id)
                res = await session.execute(stmt)
                job = res.scalar_one_or_none()
                if job and job.status != "cancelled":
                    job.status = "cancelled"
                    job.stage_description = "Execution cancelled."
                    await session.commit()
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}\n{traceback.format_exc()}")
            async with AsyncSessionLocal() as session:
                stmt = select(Job).where(Job.id == job_id)
                res = await session.execute(stmt)
                job = res.scalar_one_or_none()
                if job:
                    if job.retry_count < job.max_retries:
                        job.retry_count += 1
                        job.status = "queued"
                        job.stage_description = f"Retrying after transient error: {str(e)}"
                        # Schedule retry
                        asyncio.create_task(self.execute_job(job_id))
                    else:
                        job.status = "failed"
                        job.error_message = str(e)
                        job.stage_description = f"Failed: {str(e)}"
                    await session.commit()
        finally:
            if job_id in self._running_tasks:
                del self._running_tasks[job_id]

    async def _dispatch(self, session, job: Job) -> Dict[str, Any]:
        p = job.payload
        job_type = job.job_type

        if job_type == "story_analysis":
            bible = await story_analysis_service.run_story_analysis(session, job.project_id)
            return {"story_bible_id": bible.id, "version": bible.version}

        elif job_type == "style_analysis":
            profile = await style_analysis_service.run_style_analysis(session, job.project_id)
            return {"style_profile_id": profile.id, "version": profile.current_version}

        elif job_type == "adaptation_plan":
            plan = await serialization_service.create_adaptation_plan(session, job.project_id)
            return {"adaptation_plan_id": plan.id, "version": plan.version}

        elif job_type == "storyboard_gen":
            episode_id = p["episode_id"]
            panels = await storyboard_service.generate_episode_storyboard(session, episode_id)
            return {"panel_count": len(panels)}

        elif job_type in ("draft_generation", "final_generation"):
            panel_id = p["panel_id"]
            stage = "final" if job_type == "final_generation" else "draft"
            
            # Fetch panel
            panel_stmt = select(Panel).where(Panel.id == panel_id)
            panel_res = await session.execute(panel_stmt)
            panel = panel_res.scalar_one_or_none()
            if not panel:
                raise ValueError(f"Panel {panel_id} not found.")

            # Stale job protection check (Requirement 15 & Test 8)
            target_panel_version = p.get("panel_version", panel.version)
            is_valid = await versioning_service.check_stale_job_overwrite_guard(
                session, panel_id, target_panel_version
            )
            if not is_valid:
                raise ValueError(f"Stale generation guard triggered: Panel {panel_id} has been revised or newer asset is approved.")

            # If final generation, require storyboard approval (Requirement 2.5 & Test 6)
            if stage == "final" and not panel.is_approved:
                raise ValueError(f"Approval gate failure: Cannot generate final illustration for unapproved panel {panel_id}.")

            # Fetch active style profile
            style_stmt = (
                select(StyleProfileVersion)
                .join(StyleProfileVersion.style_profile)
                .where(StyleProfileVersion.style_profile_id == StyleProfileVersion.style_profile_id)
                .order_by(StyleProfileVersion.version_number.desc())
            )
            style_res = await session.execute(style_stmt)
            style_ver = style_res.scalars().first()
            style_data = {
                "linework_and_contours": style_ver.linework_and_contours if style_ver else "Clean manhwa ink",
                "palette_and_colors": style_ver.palette_and_colors if style_ver else ["#1A1D24", "#2E3A4D"],
                "shading_and_lighting": style_ver.shading_and_lighting if style_ver else "Soft cell shading"
            }

            img_provider = provider_factory.get_image_provider(p.get("provider_override"))
            panel_spec = {
                "panel_number": panel.panel_number,
                "shot_type": panel.shot_type,
                "camera_angle": panel.camera_angle,
                "character_action": panel.character_action,
                "environment_and_background": panel.environment_and_background,
                "focal_point": panel.focal_point,
                "local_emotion": panel.local_emotion,
                "narrative_purpose": panel.narrative_purpose
            }

            if stage == "draft":
                raw_bytes, meta = await img_provider.generate_draft(
                    panel_spec=panel_spec,
                    style_profile=style_data,
                    character_refs=[],
                    aspect_ratio=panel.aspect_ratio
                )
            else:
                raw_bytes, meta = await img_provider.generate_final(
                    panel_spec=panel_spec,
                    style_profile=style_data,
                    character_refs=[],
                    aspect_ratio=panel.aspect_ratio
                )

            # Save generated image to storage
            prefix = "draft" if stage == "draft" else "final"
            storage_key, chk, fsize = storage_service.save_bytes(
                "assets", f"{prefix}_panel_{panel.panel_number:02d}_{panel.id[:6]}.png", raw_bytes
            )

            # Create or update Asset and AssetVersion records
            asset_stmt = select(Asset).where(Asset.panel_id == panel.id)
            asset_res = await session.execute(asset_stmt)
            asset = asset_res.scalar_one_or_none()
            if not asset:
                asset = Asset(
                    project_id=job.project_id,
                    panel_id=panel.id,
                    asset_type="panel_illustration",
                    current_version=1,
                    status="generated"
                )
                session.add(asset)
                await session.flush()
                asset_ver_num = 1
            else:
                asset.current_version += 1
                asset_ver_num = asset.current_version

            asset_version = AssetVersion(
                asset_id=asset.id,
                version_number=asset_ver_num,
                storage_key=storage_key,
                stage=stage,
                provider=meta.get("provider", "mock"),
                model_version=meta.get("model_version", "v1.0"),
                model_settings={},
                prompt_used=meta.get("prompt_used", ""),
                style_profile_version=style_ver.version_number if style_ver else 1,
                character_reference_ids=[],
                estimated_cost_usd=meta.get("cost_usd", 0.0),
                actual_cost_usd=meta.get("cost_usd", 0.0),
                duration_seconds=meta.get("duration_seconds", 0.5),
                is_approved=False,
                is_mock=meta.get("is_mock", True)
            )
            session.add(asset_version)
            await session.flush()

            # Record dependencies
            await versioning_service.record_dependencies(
                session,
                asset_version_id=asset_version.id,
                panel_id=panel.id,
                panel_version=panel.version,
                style_profile_id=style_ver.style_profile_id if style_ver else "none",
                style_version=style_ver.version_number if style_ver else 1,
                character_refs=[]
            )

            # Assign active asset to panel
            panel.active_asset_id = asset.id
            await session.commit()
            return {"asset_id": asset.id, "asset_version_id": asset_version.id, "storage_key": storage_key}

        elif job_type == "panel_edit":
            asset_id = p["asset_id"]
            instruction = p["instruction"]
            target_region = p.get("target_region")

            # Load active asset version
            ver_stmt = select(AssetVersion).where(AssetVersion.asset_id == asset_id).order_by(AssetVersion.version_number.desc())
            ver_res = await session.execute(ver_stmt)
            current_ver = ver_res.scalars().first()
            if not current_ver:
                raise ValueError(f"Asset {asset_id} has no versions to edit.")

            orig_bytes = storage_service.read_bytes(current_ver.storage_key)
            img_provider = provider_factory.get_image_provider()
            edited_bytes, meta = await img_provider.edit_image(orig_bytes, instruction, target_region)

            # Save edited version
            storage_key, chk, fsize = storage_service.save_bytes("assets", f"edit_{asset_id[:6]}.png", edited_bytes)
            
            asset_stmt = select(Asset).where(Asset.id == asset_id)
            a_res = await session.execute(asset_stmt)
            asset = a_res.scalar_one_or_none()
            asset.current_version += 1

            new_ver = AssetVersion(
                asset_id=asset.id,
                version_number=asset.current_version,
                storage_key=storage_key,
                stage="edit",
                provider=meta.get("provider", "mock"),
                model_version=meta.get("model_version", "v1.0"),
                prompt_used=instruction,
                parent_asset_version_id=current_ver.id,
                style_profile_version=current_ver.style_profile_version,
                character_reference_ids=current_ver.character_reference_ids,
                estimated_cost_usd=0.0,
                actual_cost_usd=0.0,
                duration_seconds=0.3,
                is_approved=False,
                is_mock=True
            )
            session.add(new_ver)
            await session.commit()
            return {"asset_version_id": new_ver.id, "storage_key": storage_key}

        elif job_type == "episode_export":
            episode_id = p["episode_id"]
            require_all_approved = p.get("require_all_approved", False)
            export_rec = await webtoon_exporter.export_episode(
                session, episode_id=episode_id, require_all_approved=require_all_approved
            )
            return {"export_id": export_rec.id, "storage_key": export_rec.storage_key, "total_height_px": export_rec.total_height_px}

        return {}

job_runner = JobRunner()
