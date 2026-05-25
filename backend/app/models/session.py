"""
session.py — DiscoverySession ORM model. Tracks the AI-guided discovery conversation.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DiscoverySession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default="greeting")
    ai_partner_style: Mapped[str] = mapped_column(String(30), nullable=False, default="strategist")
    messages: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    scope_module_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="sessions")
