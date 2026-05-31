"""
blog_post.py — Blog posts authored by admins for the public marketing site
(tutorials, tips, conversion content). Public read, admin write.

Drafts (`published = False`) are admin-only; published posts are public and
fuel the conversion funnel + SEO. Body is Markdown rendered on the frontend.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BlogPost(Base):
    """A blog post. Published posts are public; drafts are admin-only."""

    __tablename__ = "blog_posts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    slug: Mapped[str] = mapped_column(String(300), nullable=False, unique=True, index=True)
    excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)  # SEO meta description / card teaser
    body: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown
    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # OG image / card cover
    tags: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # ["tutorial", "tips", ...]
    author_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # set on first publish; powers ordering + sitemap lastmod
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
