from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, JSON, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class StoryBible(Base, TimestampMixin):
    __tablename__ = "story_bibles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    premise: Mapped[str] = mapped_column(Text, nullable=False)
    genre: Mapped[str] = mapped_column(String(100), default="General Fiction")
    target_audience: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    narrative_tone: Mapped[str] = mapped_column(String(200), default="")
    world_rules: Mapped[list] = mapped_column(JSON, default=list)
    themes: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    uncertainties: Mapped[list] = mapped_column(JSON, default=list)

    characters: Mapped[List["Character"]] = relationship("Character", back_populates="story_bible", cascade="all, delete-orphan", lazy="selectin")
    events: Mapped[List["StoryEvent"]] = relationship("StoryEvent", back_populates="story_bible", cascade="all, delete-orphan", lazy="selectin")
    continuity_facts: Mapped[List["ContinuityFact"]] = relationship("ContinuityFact", back_populates="story_bible", cascade="all, delete-orphan", lazy="selectin")
    relationships: Mapped[List["Relationship"]] = relationship("Relationship", back_populates="story_bible", cascade="all, delete-orphan", lazy="selectin")

class Character(Base, TimestampMixin):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    story_bible_id: Mapped[str] = mapped_column(String(36), ForeignKey("story_bibles.id"), nullable=False)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    role: Mapped[str] = mapped_column(String(50), default="supporting")
    personality_summary: Mapped[str] = mapped_column(Text, default="")
    voice_and_mannerisms: Mapped[str] = mapped_column(Text, default="")
    active_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    story_bible: Mapped["StoryBible"] = relationship("StoryBible", back_populates="characters", lazy="selectin")
    versions: Mapped[List["CharacterVersion"]] = relationship("CharacterVersion", back_populates="character", cascade="all, delete-orphan", lazy="selectin")

class CharacterVersion(Base, TimestampMixin):
    __tablename__ = "character_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    character_id: Mapped[str] = mapped_column(String(36), ForeignKey("characters.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    label: Mapped[str] = mapped_column(String(100), default="Default Outfit / Appearance")
    physical_appearance: Mapped[str] = mapped_column(Text, default="")
    hair_style_and_color: Mapped[str] = mapped_column(String(255), default="")
    clothing_and_accessories: Mapped[str] = mapped_column(Text, default="")
    distinctive_features: Mapped[str] = mapped_column(Text, default="")
    body_proportions: Mapped[str] = mapped_column(String(255), default="standard")
    story_context: Mapped[str] = mapped_column(Text, default="")
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)

    character: Mapped["Character"] = relationship("Character", back_populates="versions", lazy="selectin")

class Relationship(Base, TimestampMixin):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    story_bible_id: Mapped[str] = mapped_column(String(36), ForeignKey("story_bibles.id"), nullable=False)
    source_character_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_character_id: Mapped[str] = mapped_column(String(36), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), default="neutral")
    dynamics_description: Mapped[str] = mapped_column(Text, default="")

    story_bible: Mapped["StoryBible"] = relationship("StoryBible", back_populates="relationships", lazy="selectin")

class StoryEvent(Base, TimestampMixin):
    __tablename__ = "story_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    story_bible_id: Mapped[str] = mapped_column(String(36), ForeignKey("story_bibles.id"), nullable=False)
    chronological_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    emotional_weight: Mapped[str] = mapped_column(String(50), default="moderate")

    story_bible: Mapped["StoryBible"] = relationship("StoryBible", back_populates="events", lazy="selectin")

class ContinuityFact(Base, TimestampMixin):
    __tablename__ = "continuity_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    story_bible_id: Mapped[str] = mapped_column(String(36), ForeignKey("story_bibles.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="general")
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)

    story_bible: Mapped["StoryBible"] = relationship("StoryBible", back_populates="continuity_facts", lazy="selectin")
