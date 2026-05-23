"""
user.py — User ORM model. Represents an authenticated Ide/AI user account.
Supports both email/password and OAuth-based authentication.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """User account. hashed_password is nullable for OAuth-only users."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    account_type: Mapped[str] = mapped_column(String(20), default="free", server_default="free")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False, index=True)
    entitlement_overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    clerk_user_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    inbox_email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    preferences: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
