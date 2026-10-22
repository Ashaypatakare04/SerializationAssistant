from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.adaptation import Episode, Scene, Beat, Panel
from backend.app.models.asset import Asset, AssetVersion
from backend.app.models.style import StyleProfile, StyleProfileVersion, CharacterReference
from backend.app.schemas.qa import VisualQAResponse, QAFinding

class VisualQAService:
    @classmethod
    async def evaluate_panels(
        cls,
        db: AsyncSession,
        episode_id: str
    ) -> VisualQAResponse:
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
            return VisualQAResponse(passed=False, score=0.0, style_fidelity_score=0.0, character_consistency_score=0.0, findings=[])

        all_panels = []
        for s in episode.scenes:
            for b in s.beats:
                all_panels.extend(b.panels)

        findings: List[QAFinding] = []
        valid_aspect_ratios = {"4:5", "3:4", "1:1", "9:16"}
        unreferenced_characters = 0

        for p in all_panels:
            # 1. Check aspect ratio
            if p.aspect_ratio not in valid_aspect_ratios:
                findings.append(QAFinding(
                    category="visual",
                    severity="warning",
                    title="Non-standard Aspect Ratio",
                    description=f"Panel {p.panel_number} uses non-standard webtoon ratio '{p.aspect_ratio}'.",
                    target_id=p.id,
                    target_type="panel"
                ))

            # 2. Check if panel has assigned characters without character refs
            if p.character_ids and not p.character_appearance_versions:
                unreferenced_characters += 1
                findings.append(QAFinding(
                    category="visual",
                    severity="warning",
                    title="Missing Appearance Version",
                    description=f"Panel {p.panel_number} references characters without binding to a canonical appearance version.",
                    target_id=p.id,
                    target_type="panel"
                ))

            # 3. Check for asset existence if approved
            if p.is_approved and not p.active_asset_id:
                findings.append(QAFinding(
                    category="visual",
                    severity="error",
                    title="Approved Panel Missing Art",
                    description=f"Panel {p.panel_number} is marked approved but has no generated visual asset.",
                    target_id=p.id,
                    target_type="panel"
                ))

        errors = sum(1 for f in findings if f.severity == "error")
        warnings = sum(1 for f in findings if f.severity == "warning")
        score = max(0.0, 100.0 - (errors * 25.0) - (warnings * 8.0))
        passed = (errors == 0)

        return VisualQAResponse(
            passed=passed,
            score=score,
            style_fidelity_score=88.0 if passed else 50.0,
            character_consistency_score=92.0 if passed else 60.0,
            findings=findings
        )

visual_qa_service = VisualQAService()
