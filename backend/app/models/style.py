from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, JSON, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class ReferenceAsset(Base, TimestampMixin):
    __tablename__ = "reference_assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="visual_style")
    label: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str] = mapped_column(String(100), default="image/png")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class ReferenceCollection(Base, TimestampMixin):
    __tablename__ = "reference_collections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), default="general")
    asset_ids: Mapped[list] = mapped_column(JSON, default=list)

class StyleProfile(Base, TimestampMixin):
    __tablename__ = "style_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="draft")

    versions: Mapped[List["StyleProfileVersion"]] = relationship("StyleProfileVersion", back_populates="style_profile", cascade="all, delete-orphan", lazy="selectin")

class StyleProfileVersion(Base, TimestampMixin):
    __tablename__ = "style_profile_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    style_profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("style_profiles.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    linework_and_contours: Mapped[str] = mapped_column(Text, default="")
    anatomy_and_proportions: Mapped[str] = mapped_column(Text, default="")
    facial_features_and_expressions: Mapped[str] = mapped_column(Text, default="")
    palette_and_colors: Mapped[list] = mapped_column(JSON, default=list)
    color_relationships: Mapped[str] = mapped_column(Text, default="")
    shading_and_lighting: Mapped[str] = mapped_column(Text, default="")
    texture_and_rendering: Mapped[str] = mapped_column(Text, default="")
    background_treatment: Mapped[str] = mapped_column(Text, default="")
    composition_conventions: Mapped[str] = mapped_column(Text, default="")
    degree_of_stylization: Mapped[str] = mapped_column(String(100), default="high")
    reference_isolation_notes: Mapped[str] = mapped_column(Text, default="Style-only extraction. No narrative borrowing.")
    uncertainties: Mapped[list] = mapped_column(JSON, default=list)
    reference_asset_ids: Mapped[list] = mapped_column(JSON, default=list)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    style_profile: Mapped["StyleProfile"] = relationship("StyleProfile", back_populates="versions", lazy="selectin")

class CharacterReference(Base, TimestampMixin):
    __tablename__ = "character_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    character_id: Mapped[str] = mapped_column(String(36), ForeignKey("characters.id"), nullable=False)
    reference_asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("reference_assets.id"), nullable=False)
    character_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    relevance_notes: Mapped[str] = mapped_column(Text, default="")
    is_primary_sheet: Mapped[bool] = mapped_column(Boolean, default=False)
