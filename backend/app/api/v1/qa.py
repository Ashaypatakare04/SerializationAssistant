from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_db
from backend.app.schemas.qa import FullQAReport
from backend.app.qa.narrative_qa import narrative_qa_service
from backend.app.qa.visual_qa import visual_qa_service
from backend.app.qa.sequence_qa import sequence_qa_service

router = APIRouter(tags=["Quality Assurance"])

@router.get("/episodes/{episode_id}/qa-report", response_model=FullQAReport)
async def get_episode_qa_report(
    episode_id: str,
    db: AsyncSession = Depends(get_db)
):
    narrative_res = await narrative_qa_service.evaluate_episode(db, episode_id)
    visual_res = await visual_qa_service.evaluate_panels(db, episode_id)
    sequence_res = await sequence_qa_service.evaluate_sequence(db, episode_id)

    overall_passed = narrative_res.passed and visual_res.passed and sequence_res.passed
    overall_status = "passed" if overall_passed else "review_required"

    return FullQAReport(
        overall_status=overall_status,
        narrative=narrative_res,
        visual=visual_res,
        sequence=sequence_res
    )
