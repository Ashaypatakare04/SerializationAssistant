from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class DialogueSegmentCreate(BaseModel):
    segment_type: str = "speech_bubble"
    speaker_character_id: Optional[str] = None
    speaker_name: str = ""
    text_content: str
    order_in_panel: int = 1
    position_hint: str = "top_right"

class DialogueSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    panel_id: str
    segment_type: str
    speaker_character_id: Optional[str]
    speaker_name: str
    text_content: str
    order_in_panel: int
    position_hint: str

class PanelUpdate(BaseModel):
    narrative_purpose: Optional[str] = None
    source_locator: Optional[str] = None
    character_ids: Optional[List[str]] = None
    character_appearance_versions: Optional[Dict[str, int]] = None
    shot_type: Optional[str] = None
    camera_angle: Optional[str] = None
    composition_notes: Optional[str] = None
    focal_point: Optional[str] = None
    aspect_ratio: Optional[str] = None
    character_action: Optional[str] = None
    expression_and_body_language: Optional[str] = None
    environment_and_background: Optional[str] = None
    lighting_direction: Optional[str] = None
    local_emotion: Optional[str] = None
    vertical_spacing_after_px: Optional[int] = None
    is_approved: Optional[bool] = None

class PanelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    beat_id: str
    panel_number: int
    narrative_purpose: str
    source_locator: Optional[str]
    character_ids: List[str]
    character_appearance_versions: Dict[str, Any]
    shot_type: str
    camera_angle: str
    composition_notes: str
    focal_point: str
    aspect_ratio: str
    character_action: str
    expression_and_body_language: str
    environment_and_background: str
    lighting_direction: str
    local_emotion: str
    vertical_spacing_after_px: int
    version: int
    is_approved: bool
    approved_by: Optional[str]
    active_asset_id: Optional[str]
    dialogues: List[DialogueSegmentResponse] = []

class BeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scene_id: str
    beat_number: int
    dominant_emotion: str
    secondary_emotion: Optional[str]
    emotional_intensity: int
    emotional_progression: str
    narrative_action: str
    visual_exaggeration_constraint: str
    panels: List[PanelResponse] = []

class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    episode_id: str
    scene_number: int
    title: str
    narrative_purpose: str
    environment: str
    time_of_day: str
    pacing_note: str
    beats: List[BeatResponse] = []

class EpisodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    adaptation_plan_id: str
    episode_number: int
    title: str
    premise_and_purpose: str
    source_sections_covered: List[Any]
    opening_hook: str
    ending_cliffhanger_or_beat: str
    target_panel_count: int
    status: str
    scenes: List[SceneResponse] = []

class AdaptationPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    version: int
    title: str
    target_episodes_estimate: int
    pacing_strategy: str
    story_bible_version: int
    status: str
    is_approved: bool
    approved_by: Optional[str]
    episodes: List[EpisodeResponse] = []
