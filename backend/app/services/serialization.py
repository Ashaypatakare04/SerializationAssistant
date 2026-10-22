from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.project import Project
from backend.app.models.bible import StoryBible
from backend.app.models.adaptation import AdaptationPlan, Episode, Scene, Beat
from backend.app.providers.factory import provider_factory

class SerializationService:
    @classmethod
    async def create_adaptation_plan(
        cls,
        db: AsyncSession,
        project_id: str
    ) -> AdaptationPlan:
        # Require an approved or drafted story bible
        stmt = select(StoryBible).where(StoryBible.project_id == project_id).order_by(StoryBible.version.desc())
        res = await db.execute(stmt)
        story_bible = res.scalars().first()
        if not story_bible:
            raise ValueError(f"Cannot generate adaptation plan: No story bible exists for project {project_id}.")

        bible_data = {
            "premise": story_bible.premise,
            "genre": story_bible.genre,
            "narrative_tone": story_bible.narrative_tone,
            "characters": [{"id": c.id, "canonical_name": c.canonical_name, "role": c.role} for c in story_bible.characters]
        }

        # Check project config
        proj_stmt = select(Project).where(Project.id == project_id)
        proj_res = await db.execute(proj_stmt)
        proj = proj_res.scalar_one_or_none()
        config = proj.configuration if proj else {}

        llm = provider_factory.get_llm_provider()
        plan_data = await llm.propose_adaptation(bible_data, config)

        # Check existing plan version
        exist_stmt = select(AdaptationPlan).where(AdaptationPlan.project_id == project_id).order_by(AdaptationPlan.version.desc())
        exist_res = await db.execute(exist_stmt)
        exist_plan = exist_res.scalars().first()
        version = (exist_plan.version + 1) if exist_plan else 1

        plan = AdaptationPlan(
            project_id=project_id,
            version=version,
            title=plan_data.get("title", f"Adaptation Plan v{version}"),
            target_episodes_estimate=plan_data.get("target_episodes_estimate", 1),
            pacing_strategy=plan_data.get("pacing_strategy", "standard_webtoon"),
            story_bible_version=story_bible.version,
            status="draft",
            is_approved=False
        )
        db.add(plan)
        await db.flush()

        # Add proposed episodes, scenes, beats
        for ep_data in plan_data.get("episodes", []):
            episode = Episode(
                adaptation_plan_id=plan.id,
                episode_number=ep_data.get("episode_number", 1),
                title=ep_data.get("title", f"Episode {ep_data.get('episode_number', 1)}"),
                premise_and_purpose=ep_data.get("premise_and_purpose", ""),
                source_sections_covered=ep_data.get("source_sections_covered", []),
                opening_hook=ep_data.get("opening_hook", ""),
                ending_cliffhanger_or_beat=ep_data.get("ending_cliffhanger_or_beat", ""),
                target_panel_count=ep_data.get("target_panel_count", 8),
                status="planning"
            )
            db.add(episode)
            await db.flush()

            for sc_data in ep_data.get("scenes", []):
                scene = Scene(
                    episode_id=episode.id,
                    scene_number=sc_data.get("scene_number", 1),
                    title=sc_data.get("title", f"Scene {sc_data.get('scene_number', 1)}"),
                    narrative_purpose=sc_data.get("narrative_purpose", ""),
                    environment=sc_data.get("environment", ""),
                    time_of_day=sc_data.get("time_of_day", "day"),
                    pacing_note=sc_data.get("pacing_note", "moderate")
                )
                db.add(scene)
                await db.flush()

                for b_data in sc_data.get("beats", []):
                    beat = Beat(
                        scene_id=scene.id,
                        beat_number=b_data.get("beat_number", 1),
                        dominant_emotion=b_data.get("dominant_emotion", "neutral"),
                        secondary_emotion=b_data.get("secondary_emotion"),
                        emotional_intensity=b_data.get("emotional_intensity", 5),
                        emotional_progression=b_data.get("emotional_progression", ""),
                        narrative_action=b_data.get("narrative_action", ""),
                        visual_exaggeration_constraint=b_data.get("visual_exaggeration_constraint", "grounded")
                    )
                    db.add(beat)

        if proj:
            proj.current_stage = "adaptation_planning"

        await db.commit()
        await db.refresh(plan)
        return plan

serialization_service = SerializationService()
