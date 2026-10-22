from typing import Optional, List
from sqlalchemy import String, Text, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.models.base import Base, TimestampMixin, generate_uuid

class User(Base, TimestampMixin):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    projects: Mapped[List["Project"]] = relationship("Project", back_populates="owner", cascade="all, delete-orphan", lazy="selectin")

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_format: Mapped[str] = mapped_column(String(50), default="webtoon_vertical")
    current_stage: Mapped[str] = mapped_column(String(50), default="source_intake")
    status: Mapped[str] = mapped_column(String(50), default="active")
    configuration: Mapped[dict] = mapped_column(JSON, default=dict)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    owner: Mapped["User"] = relationship("User", back_populates="projects", lazy="selectin")
    documents: Mapped[List["SourceDocument"]] = relationship("SourceDocument", back_populates="project", cascade="all, delete-orphan", lazy="selectin")
    members: Mapped[List["ProjectMember"]] = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan", lazy="selectin")

class ProjectMember(Base, TimestampMixin):
    __tablename__ = "project_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="editor")

    project: Mapped["Project"] = relationship("Project", back_populates="members", lazy="selectin")

class SourceDocument(Base, TimestampMixin):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="text/plain")
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending")
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_info: Mapped[dict] = mapped_column(JSON, default=dict)

    project: Mapped["Project"] = relationship("Project", back_populates="documents", lazy="selectin")
    sections: Mapped[List["SourceSection"]] = relationship("SourceSection", back_populates="document", cascade="all, delete-orphan", lazy="selectin")

class SourceSection(Base, TimestampMixin):
    __tablename__ = "source_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("source_documents.id"), nullable=False)
    section_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_char: Mapped[int] = mapped_column(Integer, default=0)
    end_char: Mapped[int] = mapped_column(Integer, default=0)

    document: Mapped["SourceDocument"] = relationship("SourceDocument", back_populates="sections", lazy="selectin")
