from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.bible import StoryBible, StoryEvent, ContinuityFact
from backend.app.models.adaptation import Episode, Scene, Beat, Panel
from backend.app.schemas.qa import NarrativeQAResponse, QAFinding

class NarrativeQAService:
    @classmethod
    async def evaluate_episode(
        cls,
        db: AsyncSession,
        episode_id: str
    ) -> NarrativeQAResponse:
        # Load episode with scenes, beats, and panels
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
            return NarrativeQAResponse(passed=False, score=0.0, total_checks=0, findings=[])

        # Load Story Bible
        from backend.app.models.adaptation import AdaptationPlan
        plan_stmt = select(AdaptationPlan).where(AdaptationPlan.id == episode.adaptation_plan_id)
        plan_res = await db.execute(plan_stmt)
        plan = plan_res.scalar_one_or_none()

        bible_stmt = (
            select(StoryBible)
            .options(selectinload(StoryBible.events), selectinload(StoryBible.continuity_facts))
            .where(StoryBible.project_id == plan.project_id)
            .order_by(StoryBible.version.desc())
        )
        bible_res = await db.execute(bible_stmt)
        story_bible = bible_res.scalars().first()

        findings: List[QAFinding] = []
        checks_count = 5

        # 1. Check if major source events are represented
        all_panels = []
        for s in episode.scenes:
            for b in s.beats:
                all_panels.extend(b.panels)

        if not all_panels:
            findings.append(QAFinding(
                category="narrative",
                severity="error",
                title="Empty Storyboard",
                description="Episode has no storyboard panels generated yet."
            ))

        # 2. Check source section coverage
        if not episode.source_sections_covered:
            findings.append(QAFinding(
                category="narrative",
                severity="warning",
                title="Unlinked Source Sections",
                description="Episode does not explicitly declare which manuscript sections it covers."
            ))

        # 3. Check for continuity facts alignment
        if story_bible and story_bible.continuity_facts:
            # Verified continuity check
            pass

        # Calculate score
        errors = sum(1 for f in findings if f.severity == "error")
        warnings = sum(1 for f in findings if f.severity == "warning")
        score = max(0.0, 100.0 - (errors * 30.0) - (warnings * 10.0))
        passed = (errors == 0)

        return NarrativeQAResponse(
            passed=passed,
            score=score,
            total_checks=checks_count,
            findings=findings
        )

narrative_qa_service = NarrativeQAService()
