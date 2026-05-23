"""
project.py — Project ORM model. A user's ideation workspace containing all design artifacts.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, default="custom")
    audience: Mapped[str] = mapped_column(String(50), nullable=False, default="consumers")
    complexity: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    tone: Mapped[str] = mapped_column(String(50), nullable=False, default="casual")
    accent_color: Mapped[str] = mapped_column(String(20), nullable=False, default="#00E5FF")
    pathway_id: Mapped[str] = mapped_column(String(50), nullable=False, default="software_product")
    ai_partner_style: Mapped[str] = mapped_column(String(30), nullable=False, default="strategist")
    primary_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    secondary_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pathway_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # "v1" = legacy Discovery → PathwayReview → per-module sessions flow.
    # "v2" = unified Discovery → Design Kit flow (assembled up-front).
    flow_version: Mapped[str] = mapped_column(String(10), nullable=False, default="v2", server_default="v2", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="projects")
    sessions = relationship("DiscoverySession", back_populates="project", cascade="all, delete-orphan")
    design_sheet = relationship("DesignSheet", back_populates="project", uselist=False, cascade="all, delete-orphan")
    blocks = relationship("Block", back_populates="project", cascade="all, delete-orphan")
    pipeline_nodes = relationship("PipelineNode", back_populates="project", cascade="all, delete-orphan")
    prompt_kits = relationship("PromptKit", back_populates="project", cascade="all, delete-orphan")
    versions = relationship("Version", back_populates="project", cascade="all, delete-orphan")
    market_analysis = relationship("MarketAnalysis", back_populates="project", uselist=False, cascade="all, delete-orphan")
    snapshots = relationship("ProjectSnapshot", back_populates="project", cascade="all, delete-orphan")
    shares = relationship("ProjectShare", back_populates="project", cascade="all, delete-orphan")
    sprint_plan = relationship("SprintPlan", back_populates="project", uselist=False, cascade="all, delete-orphan")
    module_artifacts = relationship("ModuleArtifact", back_populates="project", cascade="all, delete-orphan")
    module_pathway = relationship("ModulePathway", back_populates="project", uselist=False, cascade="all, delete-orphan")
    module_responses = relationship("ModuleResponse", back_populates="project", cascade="all, delete-orphan")
