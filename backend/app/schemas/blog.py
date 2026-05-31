"""
blog.py — Pydantic v2 schemas for the blog.

Public read models (`BlogPostOut`, `BlogPostSummary`) + admin write models
(`BlogPostCreate`, `BlogPostUpdate`) + the paginated admin list response.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BlogPostCreate(BaseModel):
    """Admin create payload. Slug is derived from the title when omitted."""

    title: str = Field(min_length=1, max_length=300)
    slug: str | None = Field(default=None, max_length=300)
    excerpt: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1)
    cover_image_url: str | None = None
    tags: list[str] | None = None
    author_name: str | None = Field(default=None, max_length=120)
    published: bool = False


class BlogPostUpdate(BaseModel):
    """Admin update payload — every field optional (PATCH semantics)."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    slug: str | None = Field(default=None, min_length=1, max_length=300)
    excerpt: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    cover_image_url: str | None = None
    tags: list[str] | None = None
    author_name: str | None = Field(default=None, max_length=120)
    published: bool | None = None


class BlogPostOut(BaseModel):
    """Full post (public single-post view + admin editor)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    excerpt: str | None = None
    body: str
    cover_image_url: str | None = None
    tags: list[str] | None = None
    author_name: str | None = None
    published: bool
    published_at: datetime | None = None
    view_count: int
    created_at: datetime
    updated_at: datetime


class BlogPostSummary(BaseModel):
    """List item — no body, for listings + sitemap."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    excerpt: str | None = None
    cover_image_url: str | None = None
    tags: list[str] | None = None
    author_name: str | None = None
    published: bool
    published_at: datetime | None = None
    view_count: int
    created_at: datetime


class BlogListResponse(BaseModel):
    """Paginated admin listing (includes drafts)."""

    items: list[BlogPostSummary]
    total: int
    page: int
    per_page: int
