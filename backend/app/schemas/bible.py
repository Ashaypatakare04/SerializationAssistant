from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class CharacterVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    character_id: str
    version_number: int
    label: str
    physical_appearance: str
    hair_style_and_color: str
    clothing_and_accessories: str
    distinctive_features: str
    body_proportions: str
    story_context: str
    is_approved: bool

class CharacterCreate(BaseModel):
    canonical_name: str
    aliases: List[str] = []
    role: str = "supporting"
    personality_summary: str = ""
    voice_and_mannerisms: str = ""
    physical_appearance: str = ""
    hair_style_and_color: str = ""
    clothing_and_accessories: str = ""
    distinctive_features: str = ""
    body_proportions: str = "standard"

class CharacterUpdate(BaseModel):
    canonical_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    role: Optional[str] = None
    personality_summary: Optional[str] = None
    voice_and_mannerisms: Optional[str] = None
    physical_appearance: Optional[str] = None
    hair_style_and_color: Optional[str] = None
    clothing_and_accessories: Optional[str] = None
    distinctive_features: Optional[str] = None
    body_proportions: Optional[str] = None

class CharacterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    story_bible_id: str
    canonical_name: str
    aliases: List[str]
    role: str
    personality_summary: str
    voice_and_mannerisms: str
    active_version_id: Optional[str]
    versions: List[CharacterVersionResponse] = []

class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_character_id: str
    target_character_id: str
    relationship_type: str
    dynamics_description: str

class StoryEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chronological_order: int
    title: str
    summary: str
    source_locator: Optional[str]
    emotional_weight: str

class ContinuityFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    category: str
    statement: str
    source_locator: Optional[str]
    is_confirmed: bool

class StoryBibleUpdate(BaseModel):
    premise: Optional[str] = None
    genre: Optional[str] = None
    target_audience: Optional[str] = None
    narrative_tone: Optional[str] = None
    world_rules: Optional[List[Dict[str, Any]]] = None
    themes: Optional[List[str]] = None
    uncertainties: Optional[List[Dict[str, Any]]] = None

class StoryBibleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    version: int
    premise: str
    genre: str
    target_audience: Optional[str]
    narrative_tone: str
    world_rules: List[Any]
    themes: List[Any]
    status: str
    uncertainties: List[Any]
    created_at: datetime
    updated_at: datetime
    characters: List[CharacterResponse] = []
    events: List[StoryEventResponse] = []
    continuity_facts: List[ContinuityFactResponse] = []
    relationships: List[RelationshipResponse] = []
