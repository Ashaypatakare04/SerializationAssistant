from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, JSON, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class AdaptationPlan(Base, TimestampMixin):
    __tablename__ = "adaptation_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_episodes_estimate: Mapped[int] = mapped_column(Integer, default=1)
    pacing_strategy: Mapped[str] = mapped_column(String(100), default="balanced_webtoon")
    story_bible_version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    episodes: Mapped[List["Episode"]] = relationship("Episode", back_populates="adaptation_plan", cascade="all, delete-orphan", lazy="selectin")

class Episode(Base, TimestampMixin):
    __tablename__ = "episodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    adaptation_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("adaptation_plans.id"), nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    premise_and_purpose: Mapped[str] = mapped_column(Text, default="")
    source_sections_covered: Mapped[list] = mapped_column(JSON, default=list)
    opening_hook: Mapped[str] = mapped_column(Text, default="")
    ending_cliffhanger_or_beat: Mapped[str] = mapped_column(Text, default="")
    target_panel_count: Mapped[int] = mapped_column(Integer, default=8)
    status: Mapped[str] = mapped_column(String(50), default="planning")

    adaptation_plan: Mapped["AdaptationPlan"] = relationship("AdaptationPlan", back_populates="episodes", lazy="selectin")
    scenes: Mapped[List["Scene"]] = relationship("Scene", back_populates="episode", cascade="all, delete-orphan", lazy="selectin")

class Scene(Base, TimestampMixin):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    episode_id: Mapped[str] = mapped_column(String(36), ForeignKey("episodes.id"), nullable=False)
    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    narrative_purpose: Mapped[str] = mapped_column(Text, default="")
    environment: Mapped[str] = mapped_column(String(255), default="")
    time_of_day: Mapped[str] = mapped_column(String(50), default="day")
    pacing_note: Mapped[str] = mapped_column(String(100), default="moderate")

    episode: Mapped["Episode"] = relationship("Episode", back_populates="scenes", lazy="selectin")
    beats: Mapped[List["Beat"]] = relationship("Beat", back_populates="scene", cascade="all, delete-orphan", lazy="selectin")

class Beat(Base, TimestampMixin):
    __tablename__ = "beats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scene_id: Mapped[str] = mapped_column(String(36), ForeignKey("scenes.id"), nullable=False)
    beat_number: Mapped[int] = mapped_column(Integer, nullable=False)
    dominant_emotion: Mapped[str] = mapped_column(String(100), default="neutral")
    secondary_emotion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emotional_intensity: Mapped[int] = mapped_column(Integer, default=5)
    emotional_progression: Mapped[str] = mapped_column(Text, default="")
    narrative_action: Mapped[str] = mapped_column(Text, default="")
    visual_exaggeration_constraint: Mapped[str] = mapped_column(String(200), default="grounded; avoid chibi unless specified")

    scene: Mapped["Scene"] = relationship("Scene", back_populates="beats", lazy="selectin")
    panels: Mapped[List["Panel"]] = relationship("Panel", back_populates="beat", cascade="all, delete-orphan", lazy="selectin")

class Panel(Base, TimestampMixin):
    __tablename__ = "panels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    beat_id: Mapped[str] = mapped_column(String(36), ForeignKey("beats.id"), nullable=False)
    panel_number: Mapped[int] = mapped_column(Integer, nullable=False)
    narrative_purpose: Mapped[str] = mapped_column(Text, default="")
    source_locator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    character_ids: Mapped[list] = mapped_column(JSON, default=list)
    character_appearance_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    shot_type: Mapped[str] = mapped_column(String(50), default="medium_shot")
    camera_angle: Mapped[str] = mapped_column(String(50), default="eye_level")
    composition_notes: Mapped[str] = mapped_column(Text, default="")
    focal_point: Mapped[str] = mapped_column(String(255), default="")
    aspect_ratio: Mapped[str] = mapped_column(String(20), default="4:5")
    character_action: Mapped[str] = mapped_column(Text, default="")
    expression_and_body_language: Mapped[str] = mapped_column(Text, default="")
    environment_and_background: Mapped[str] = mapped_column(Text, default="")
    lighting_direction: Mapped[str] = mapped_column(Text, default="")
    local_emotion: Mapped[str] = mapped_column(String(100), default="")
    vertical_spacing_after_px: Mapped[int] = mapped_column(Integer, default=60)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active_asset_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    beat: Mapped["Beat"] = relationship("Beat", back_populates="panels", lazy="selectin")
    dialogues: Mapped[List["DialogueSegment"]] = relationship("DialogueSegment", back_populates="panel", cascade="all, delete-orphan", lazy="selectin")

class DialogueSegment(Base, TimestampMixin):
    __tablename__ = "dialogue_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    panel_id: Mapped[str] = mapped_column(String(36), ForeignKey("panels.id"), nullable=False)
    segment_type: Mapped[str] = mapped_column(String(50), default="speech_bubble")
    speaker_character_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    speaker_name: Mapped[str] = mapped_column(String(100), default="")
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    order_in_panel: Mapped[int] = mapped_column(Integer, default=1)
    position_hint: Mapped[str] = mapped_column(String(50), default="top_right")

    panel: Mapped["Panel"] = relationship("Panel", back_populates="dialogues", lazy="selectin")
