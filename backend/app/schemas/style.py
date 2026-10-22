from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ReferenceAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    storage_key: str
    role: str
    label: str
    description: Optional[str]
    width: int
    height: int
    mime_type: str
    is_active: bool
    created_at: datetime

class StyleProfileVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    style_profile_id: str
    version_number: int
    linework_and_contours: str
    anatomy_and_proportions: str
    facial_features_and_expressions: str
    palette_and_colors: List[Any]
    color_relationships: str
    shading_and_lighting: str
    texture_and_rendering: str
    background_treatment: str
    composition_conventions: str
    degree_of_stylization: str
    reference_isolation_notes: str
    uncertainties: List[Any]
    reference_asset_ids: List[str]
    is_approved: bool
    approved_by: Optional[str]
    created_at: datetime

class StyleProfileUpdate(BaseModel):
    linework_and_contours: Optional[str] = None
    anatomy_and_proportions: Optional[str] = None
    facial_features_and_expressions: Optional[str] = None
    palette_and_colors: Optional[List[Any]] = None
    color_relationships: Optional[str] = None
    shading_and_lighting: Optional[str] = None
    texture_and_rendering: Optional[str] = None
    background_treatment: Optional[str] = None
    composition_conventions: Optional[str] = None
    degree_of_stylization: Optional[str] = None
    reference_isolation_notes: Optional[str] = None
    uncertainties: Optional[List[Any]] = None

class StyleProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    current_version: int
    status: str
    versions: List[StyleProfileVersionResponse] = []

class CharacterReferenceCreate(BaseModel):
    character_id: str
    reference_asset_id: str
    character_version_id: Optional[str] = None
    relevance_notes: str = ""
    is_primary_sheet: bool = False

class CharacterReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    character_id: str
    reference_asset_id: str
    character_version_id: Optional[str]
    relevance_notes: str
    is_primary_sheet: bool
