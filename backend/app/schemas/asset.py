from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class AssetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    version_number: int
    storage_key: str
    thumbnail_key: Optional[str]
    stage: str
    provider: str
    model_version: str
    model_settings: Dict[str, Any]
    prompt_used: str
    negative_prompt: Optional[str]
    style_profile_version: int
    character_reference_ids: List[str]
    parent_asset_version_id: Optional[str]
    edit_mask_storage_key: Optional[str]
    estimated_cost_usd: float
    actual_cost_usd: float
    duration_seconds: float
    is_approved: bool
    is_mock: bool
    created_at: datetime

class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    panel_id: Optional[str]
    asset_type: str
    current_version: int
    status: str
    versions: List[AssetVersionResponse] = []

class GenerationJobCreate(BaseModel):
    stage: str = "draft"  # draft, final
    prompt_override: Optional[str] = None
    negative_prompt: Optional[str] = None
    provider_override: Optional[str] = None

class EditJobCreate(BaseModel):
    instruction: str
    target_region: Optional[str] = None  # e.g., "face", "clothing", "background"
    mask_storage_key: Optional[str] = None

class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    job_type: str
    status: str
    progress_percentage: int
    stage_description: str
    payload: Dict[str, Any]
    result_data: Dict[str, Any]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

class ApprovalCreate(BaseModel):
    artifact_type: str  # story_bible, adaptation_plan, storyboard, panel_asset, final_episode
    artifact_id: str
    artifact_version: int
    approved_by: str = "creator"
    comments: Optional[str] = None

class ApprovalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    artifact_type: str
    artifact_id: str
    artifact_version: int
    approved_by: str
    is_revoked: bool
    comments: Optional[str]
    created_at: datetime

class ReviewCreate(BaseModel):
    target_type: str
    target_id: str
    version_reviewed: int
    status: str  # approved, rejected, revision_requested
    notes: Optional[str] = None
    findings: List[Dict[str, Any]] = []

class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    target_type: str
    target_id: str
    version_reviewed: int
    status: str
    notes: Optional[str]
    reviewer_id: str
    findings: List[Any]
    created_at: datetime

class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    episode_id: str
    export_format: str
    storage_key: str
    manifest_data: Dict[str, Any]
    panel_count: int
    total_height_px: int
    slice_count: int
    is_verified: bool
    created_at: datetime
