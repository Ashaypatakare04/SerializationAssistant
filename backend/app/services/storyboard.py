from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.adaptation import Episode, Scene, Beat, Panel, DialogueSegment
from backend.app.models.bible import StoryBible, Character
from backend.app.models.style import StyleProfile
from backend.app.providers.factory import provider_factory

class StoryboardService:
    @classmethod
    async def generate_episode_storyboard(
        cls,
        db: AsyncSession,
        episode_id: str
    ) -> List[Panel]:
        # Fetch episode with scenes and beats
        stmt = (
            select(Episode)
            .options(
                selectinload(Episode.scenes).selectinload(Scene.beats).selectinload(Beat.panels)
            )
            .where(Episode.id == episode_id)
        )
        res = await db.execute(stmt)
        episode = res.scalar_one_or_none()
        if not episode:
            raise ValueError(f"Episode {episode_id} not found.")

        # Fetch story bible for characters
        from backend.app.models.adaptation import AdaptationPlan
        plan_stmt = select(AdaptationPlan).where(AdaptationPlan.id == episode.adaptation_plan_id)
        plan_res = await db.execute(plan_stmt)
        plan = plan_res.scalar_one_or_none()

        bible_stmt = (
            select(StoryBible)
            .options(selectinload(StoryBible.characters))
            .where(StoryBible.project_id == plan.project_id)
            .order_by(StoryBible.version.desc())
        )
        bible_res = await db.execute(bible_stmt)
        story_bible = bible_res.scalars().first()

        characters_data = [
            {"id": c.id, "canonical_name": c.canonical_name, "role": c.role}
            for c in (story_bible.characters if story_bible else [])
        ]

        llm = provider_factory.get_llm_provider()
        raw_panels = await llm.generate_storyboard(
            episode_data={"title": episode.title, "premise": episode.premise_and_purpose},
            story_bible_data={"characters": characters_data}
        )

        # Distribute panels across scenes and beats
        first_scene = episode.scenes[0] if episode.scenes else None
        first_beat = first_scene.beats[0] if first_scene and first_scene.beats else None
        second_beat = first_scene.beats[1] if first_scene and len(first_scene.beats) > 1 else first_beat

        created_panels = []
        for p_idx, p_data in enumerate(raw_panels):
            target_beat = second_beat if (p_idx >= len(raw_panels) // 2 and second_beat) else first_beat
            if not target_beat:
                continue

            panel = Panel(
                beat_id=target_beat.id,
                panel_number=p_data.get("panel_number", p_idx + 1),
                narrative_purpose=p_data.get("narrative_purpose", ""),
                character_ids=[c["id"] for c in characters_data],
                character_appearance_versions={c["id"]: 1 for c in characters_data},
                shot_type=p_data.get("shot_type", "medium_shot"),
                camera_angle=p_data.get("camera_angle", "eye_level"),
                composition_notes=p_data.get("composition_notes", ""),
                focal_point=p_data.get("focal_point", ""),
                aspect_ratio=p_data.get("aspect_ratio", "4:5"),
                character_action=p_data.get("character_action", ""),
                expression_and_body_language=p_data.get("expression_and_body_language", ""),
                environment_and_background=p_data.get("environment_and_background", ""),
                lighting_direction=p_data.get("lighting_direction", ""),
                local_emotion=p_data.get("local_emotion", ""),
                vertical_spacing_after_px=p_data.get("vertical_spacing_after_px", 60),
                version=1,
                is_approved=False
            )
            db.add(panel)
            await db.flush()

            # Add dialogues
            for d_data in p_data.get("dialogues", []):
                dialogue = DialogueSegment(
                    panel_id=panel.id,
                    segment_type=d_data.get("segment_type", "speech_bubble"),
                    speaker_name=d_data.get("speaker_name", ""),
                    text_content=d_data.get("text_content", ""),
                    order_in_panel=d_data.get("order_in_panel", 1),
                    position_hint=d_data.get("position_hint", "top_right")
                )
                db.add(dialogue)

            created_panels.append(panel)

        episode.status = "storyboarded"
        await db.commit()
        return created_panels

    @classmethod
    async def update_panel(
        cls,
        db: AsyncSession,
        panel_id: str,
        update_data: Dict[str, Any]
    ) -> Panel:
        stmt = select(Panel).where(Panel.id == panel_id)
        res = await db.execute(stmt)
        panel = res.scalar_one_or_none()
        if not panel:
            raise ValueError(f"Panel {panel_id} not found.")

        # Update fields and bump version
        for key, val in update_data.items():
            if val is not None and hasattr(panel, key):
                setattr(panel, key, val)

        panel.version += 1
        # When panel specs change, un-approve to require re-review
        panel.is_approved = False
        panel.approved_by = None

        await db.commit()
        await db.refresh(panel)
        return panel

storyboard_service = StoryboardService()
