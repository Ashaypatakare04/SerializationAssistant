from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.project import Project, SourceDocument
from backend.app.models.bible import StoryBible, Character, CharacterVersion, StoryEvent, ContinuityFact, Relationship
from backend.app.providers.factory import provider_factory

class StoryAnalysisService:
    @classmethod
    async def run_story_analysis(
        cls,
        db: AsyncSession,
        project_id: str
    ) -> StoryBible:
        # Load all source documents for project
        stmt = select(SourceDocument).where(SourceDocument.project_id == project_id)
        result = await db.execute(stmt)
        docs = result.scalars().all()
        if not docs:
            raise ValueError(f"Cannot analyze story: No source documents uploaded for project {project_id}.")

        # Concatenate text from sections
        combined_text_parts = []
        for doc in docs:
            # We can read from storage or doc metadata
            from backend.app.services.storage import storage_service
            try:
                content = storage_service.read_text(doc.storage_key)
                combined_text_parts.append(content)
            except Exception:
                combined_text_parts.append(f"Document {doc.filename}")

        full_text = "\n\n".join(combined_text_parts)

        # Get project config
        project_stmt = select(Project).where(Project.id == project_id)
        proj_res = await db.execute(project_stmt)
        project = proj_res.scalar_one_or_none()
        config = project.configuration if project else {}

        # Run extraction through active provider
        llm = provider_factory.get_llm_provider()
        analysis = await llm.analyze_story(full_text, config)

        # Check if an existing story bible exists
        bible_stmt = select(StoryBible).where(StoryBible.project_id == project_id)
        bible_res = await db.execute(bible_stmt)
        existing_bible = bible_res.scalar_one_or_none()

        version = 1
        if existing_bible:
            version = existing_bible.version + 1

        story_bible = StoryBible(
            project_id=project_id,
            version=version,
            premise=analysis.get("premise", "Extracted premise"),
            genre=analysis.get("genre", "Fiction"),
            target_audience=analysis.get("target_audience", "General"),
            narrative_tone=analysis.get("narrative_tone", "Dramatic"),
            world_rules=analysis.get("world_rules", []),
            themes=analysis.get("themes", []),
            uncertainties=analysis.get("uncertainties", []),
            status="draft"
        )
        db.add(story_bible)
        await db.flush()

        # Add characters & initial versions
        for char_data in analysis.get("characters", []):
            char = Character(
                story_bible_id=story_bible.id,
                canonical_name=char_data["canonical_name"],
                aliases=char_data.get("aliases", []),
                role=char_data.get("role", "supporting"),
                personality_summary=char_data.get("personality_summary", ""),
                voice_and_mannerisms=char_data.get("voice_and_mannerisms", "")
            )
            db.add(char)
            await db.flush()

            char_version = CharacterVersion(
                character_id=char.id,
                version_number=1,
                label="Canonical Appearance (Initial Extraction)",
                physical_appearance=char_data.get("physical_appearance", ""),
                hair_style_and_color=char_data.get("hair_style_and_color", ""),
                clothing_and_accessories=char_data.get("clothing_and_accessories", ""),
                distinctive_features=char_data.get("distinctive_features", ""),
                body_proportions=char_data.get("body_proportions", "standard"),
                story_context="Base extracted appearance",
                is_approved=False
            )
            db.add(char_version)
            await db.flush()
            char.active_version_id = char_version.id

        # Add Story Events with Source Locators
        for event_data in analysis.get("events", []):
            event = StoryEvent(
                story_bible_id=story_bible.id,
                chronological_order=event_data.get("chronological_order", 1),
                title=event_data.get("title", "Event"),
                summary=event_data.get("summary", ""),
                source_locator=event_data.get("source_locator", "Source Chapter 1"),
                emotional_weight=event_data.get("emotional_weight", "moderate")
            )
            db.add(event)

        # Add Continuity Facts
        for fact_data in analysis.get("continuity_facts", []):
            fact = ContinuityFact(
                story_bible_id=story_bible.id,
                category=fact_data.get("category", "rule"),
                statement=fact_data.get("statement", ""),
                source_locator=fact_data.get("source_locator", "Source"),
                is_confirmed=fact_data.get("is_confirmed", True)
            )
            db.add(fact)

        if project:
            project.current_stage = "story_analysis"

        await db.commit()
        await db.refresh(story_bible)
        return story_bible

story_analysis_service = StoryAnalysisService()
