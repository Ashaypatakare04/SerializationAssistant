from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, JSON, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    panel_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("panels.id"), nullable=True)
    asset_type: Mapped[str] = mapped_column(String(50), default="panel_illustration")
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="generated")

    versions: Mapped[List["AssetVersion"]] = relationship("AssetVersion", back_populates="asset", cascade="all, delete-orphan", lazy="selectin")

class AssetVersion(Base, TimestampMixin):
    __tablename__ = "asset_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    asset_id: Mapped[str] = mapped_column(String(36), ForeignKey("assets.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), default="draft")
    
    provider: Mapped[str] = mapped_column(String(100), default="mock")
    model_version: Mapped[str] = mapped_column(String(100), default="v1.0")
    model_settings: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_used: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    style_profile_version: Mapped[int] = mapped_column(Integer, default=1)
    character_reference_ids: Mapped[list] = mapped_column(JSON, default=list)
    parent_asset_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    edit_mask_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    actual_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="versions", lazy="selectin")

class AssetDependency(Base, TimestampMixin):
    __tablename__ = "asset_dependencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    asset_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("asset_versions.id"), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(36), nullable=False)
    dependency_version: Mapped[int] = mapped_column(Integer, default=1)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)

class GenerationRun(Base, TimestampMixin):
    __tablename__ = "generation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    panel_id: Mapped[str] = mapped_column(String(36), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), default="draft")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    provider: Mapped[str] = mapped_column(String(100), default="mock")
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    stage_description: Mapped[str] = mapped_column(String(255), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result_data: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_reviewed: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[str] = mapped_column(String(255), default="creator")
    findings: Mapped[list] = mapped_column(JSON, default=list)

class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    artifact_id: Mapped[str] = mapped_column(String(36), nullable=False)
    artifact_version: Mapped[int] = mapped_column(Integer, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class Export(Base, TimestampMixin):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id"), nullable=False)
    export_format: Mapped[str] = mapped_column(String(50), default="vertical_webtoon_zip")
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    manifest_data: Mapped[dict] = mapped_column(JSON, default=dict)
    panel_count: Mapped[int] = mapped_column(Integer, default=0)
    total_height_px: Mapped[int] = mapped_column(Integer, default=0)
    slice_count: Mapped[int] = mapped_column(Integer, default=1)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True)
