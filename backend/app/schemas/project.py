from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_format: str = "webtoon_vertical"
    configuration: Dict[str, Any] = Field(default_factory=dict)

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    current_stage: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None

class SourceSectionResponse(BaseModel):
    id: str
    section_index: int
    title: str
    content: str
    start_char: int
    end_char: int

    class Config:
        from_attributes = True

class SourceDocumentResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    mime_type: str
    extraction_status: str
    char_count: int
    word_count: int
    created_at: datetime
    sections: List[SourceSectionResponse] = []

    class Config:
        from_attributes = True

class ProjectResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    target_format: str
    current_stage: str
    status: str
    owner_id: str
    configuration: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    documents: List[SourceDocumentResponse] = []

    class Config:
        from_attributes = True
