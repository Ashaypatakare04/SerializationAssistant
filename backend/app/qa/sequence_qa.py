from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.adaptation import Episode, Scene, Beat, Panel, DialogueSegment
from backend.app.schemas.qa import SequenceQAResponse, QAFinding

class SequenceQAService:
    @classmethod
    async def evaluate_sequence(
        cls,
        db: AsyncSession,
        episode_id: str
    ) -> SequenceQAResponse:
        stmt = (
            select(Episode)
            .options(
                selectinload(Episode.scenes).selectinload(Scene.beats).selectinload(Beat.panels).selectinload(Panel.dialogues)
            )
            .where(Episode.id == episode_id)
        )
        res = await db.execute(stmt)
        episode = res.scalar_one_or_none()
        if not episode:
            return SequenceQAResponse(passed=False, score=0.0, pacing_score=0.0, reading_flow_score=0.0, findings=[])

        all_panels = []
        for s in episode.scenes:
            for b in s.beats:
                all_panels.extend(b.panels)

        # Sort by panel number
        all_panels.sort(key=lambda p: p.panel_number)

        findings: List[QAFinding] = []

        # 1. Sequential numbering check
        expected_num = 1
        for p in all_panels:
            if p.panel_number != expected_num:
                findings.append(QAFinding(
                    category="sequence",
                    severity="error",
                    title="Broken Reading Order",
                    description=f"Expected panel {expected_num} but found panel {p.panel_number}.",
                    target_id=p.id,
                    target_type="panel"
                ))
            expected_num += 1

        # 2. Camera framing variety check (avoid repetitive identical framing across 3+ consecutive panels)
        consecutive_identical_shots = 0
        last_shot = None
        for p in all_panels:
            if p.shot_type == last_shot:
                consecutive_identical_shots += 1
                if consecutive_identical_shots >= 3:
                    findings.append(QAFinding(
                        category="sequence",
                        severity="warning",
                        title="Repetitive Camera Framing",
                        description=f"3 or more consecutive panels use the same shot type '{p.shot_type}'. Consider varying framing to maintain visual interest.",
                        target_id=p.id,
                        target_type="panel"
                    ))
            else:
                consecutive_identical_shots = 1
                last_shot = p.shot_type

        # 3. Dialogue legibility & length check
        for p in all_panels:
            for d in p.dialogues:
                if len(d.text_content) > 250:
                    findings.append(QAFinding(
                        category="sequence",
                        severity="warning",
                        title="Excessive Dialogue in Panel",
                        description=f"Panel {p.panel_number} dialogue contains {len(d.text_content)} characters. In mobile webtoons, dialogue over 200 characters clutters artwork.",
                        target_id=d.id,
                        target_type="dialogue_segment"
                    ))

        errors = sum(1 for f in findings if f.severity == "error")
        warnings = sum(1 for f in findings if f.severity == "warning")
        score = max(0.0, 100.0 - (errors * 30.0) - (warnings * 10.0))
        passed = (errors == 0)

        return SequenceQAResponse(
            passed=passed,
            score=score,
            pacing_score=85.0 if passed else 50.0,
            reading_flow_score=90.0 if passed else 55.0,
            findings=findings
        )

sequence_qa_service = SequenceQAService()
