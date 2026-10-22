from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class QAFinding(BaseModel):
    category: str  # narrative, visual, sequence
    severity: str  # info, warning, error
    title: str
    description: str
    target_id: Optional[str] = None
    target_type: Optional[str] = None
    suggestion: Optional[str] = None

class NarrativeQAResponse(BaseModel):
    passed: bool
    score: float
    total_checks: int
    findings: List[QAFinding] = []

class VisualQAResponse(BaseModel):
    passed: bool
    score: float
    style_fidelity_score: float
    character_consistency_score: float
    findings: List[QAFinding] = []

class SequenceQAResponse(BaseModel):
    passed: bool
    score: float
    pacing_score: float
    reading_flow_score: float
    findings: List[QAFinding] = []

class FullQAReport(BaseModel):
    overall_status: str  # passed, review_required, blocked
    narrative: NarrativeQAResponse
    visual: VisualQAResponse
    sequence: SequenceQAResponse
