"""
blog.py — Blog API.

Public (no auth):
  GET  /blog/posts            list published posts (newest first)
  GET  /blog/posts/{slug}     fetch a published post by slug (+1 view)

Admin only (require_admin), audit-logged:
  GET    /blog/admin/posts        list all posts incl. drafts (paginated)
  POST   /blog/admin/posts        create a post
  GET    /blog/admin/posts/{id}   fetch any post by id (for editing)
  PATCH  /blog/admin/posts/{id}   update a post
  DELETE /blog/admin/posts/{id}   delete a post
"""
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.blog_post import BlogPost
from app.models.user import User
from app.routers.admin import require_admin
from app.schemas.blog import (
    BlogListResponse,
    BlogPostCreate,
    BlogPostOut,
    BlogPostSummary,
    BlogPostUpdate,
)
from app.services.audit_service import log_admin_action

router = APIRouter(prefix="/blog", tags=["blog"])


def slugify(value: str) -> str:
    """Lowercase, hyphenate, and strip to a URL-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "post"


async def _slug_taken(db: AsyncSession, slug: str, exclude_id: uuid.UUID | None = None) -> bool:
    q = select(BlogPost.id).where(BlogPost.slug == slug)
    if exclude_id is not None:
        q = q.where(BlogPost.id != exclude_id)
    return (await db.execute(q)).first() is not None


async def _get_post_or_404(db: AsyncSession, post_id: uuid.UUID) -> BlogPost:
    post = (await db.execute(select(BlogPost).where(BlogPost.id == post_id))).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    return post


# ── Public routes ───────────────────────────────────────────────────


@router.get("/posts", response_model=list[BlogPostSummary])
async def list_published_posts(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Public list of published posts, newest first."""
    rows = await db.execute(
        select(BlogPost)
        .where(BlogPost.published)
        .order_by(BlogPost.published_at.desc(), BlogPost.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return rows.scalars().all()


@router.get("/posts/{slug}", response_model=BlogPostOut)
async def get_published_post(slug: str, db: AsyncSession = Depends(get_db)):
    """Public fetch of a single published post by slug. Increments view count."""
    post = (
        await db.execute(select(BlogPost).where(BlogPost.slug == slug, BlogPost.published))
    ).scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blog post not found")
    post.view_count = (post.view_count or 0) + 1
    await db.flush()
    await db.refresh(post)  # flush bumps onupdate updated_at → reload before serialization
    return post


# ── Admin routes ────────────────────────────────────────────────────


@router.get("/admin/posts", response_model=BlogListResponse)
async def admin_list_posts(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status", pattern="^(published|draft)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    """All posts incl. drafts, newest first, paginated."""
    base = select(BlogPost)
    if status_filter == "published":
        base = base.where(BlogPost.published)
    elif status_filter == "draft":
        base = base.where(~BlogPost.published)

    total = (await db.execute(select(sa_func.count()).select_from(base.subquery()))).scalar() or 0
    rows = await db.execute(
        base.order_by(BlogPost.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    )
    items = [BlogPostSummary.model_validate(p) for p in rows.scalars().all()]
    return BlogListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/admin/posts", response_model=BlogPostOut, status_code=status.HTTP_201_CREATED)
async def admin_create_post(
    payload: BlogPostCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a blog post (admin-only). Audit-logged."""
    slug = slugify(payload.slug or payload.title)
    if await _slug_taken(db, slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Slug '{slug}' is already in use"
        )

    post = BlogPost(
        title=payload.title,
        slug=slug,
        excerpt=payload.excerpt,
        body=payload.body,
        cover_image_url=payload.cover_image_url,
        tags=payload.tags,
        author_name=payload.author_name,
        published=payload.published,
        published_at=datetime.now(timezone.utc) if payload.published else None,
        created_by=admin.id,
        view_count=0,
    )
    db.add(post)
    await db.flush()
    await db.refresh(post)  # load server-default created_at/updated_at before serialization
    await log_admin_action(
        db,
        admin.id,
        "blog_post_created",
        details={"post_id": str(post.id), "slug": slug, "published": payload.published},
    )
    return post


@router.get("/admin/posts/{post_id}", response_model=BlogPostOut)
async def admin_get_post(
    post_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Fetch any post (incl. drafts) by id — for the admin editor."""
    return await _get_post_or_404(db, post_id)


@router.patch("/admin/posts/{post_id}", response_model=BlogPostOut)
async def admin_update_post(
    post_id: uuid.UUID,
    payload: BlogPostUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a blog post (admin-only). Audit-logged."""
    post = await _get_post_or_404(db, post_id)
    data = payload.model_dump(exclude_unset=True)

    if data.get("slug") is not None:
        new_slug = slugify(data["slug"])
        if await _slug_taken(db, new_slug, exclude_id=post.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=f"Slug '{new_slug}' is already in use"
            )
        post.slug = new_slug
    data.pop("slug", None)

    if "published" in data and data["published"] is not None:
        becoming_published = data["published"] and not post.published
        post.published = data["published"]
        if becoming_published and post.published_at is None:
            post.published_at = datetime.now(timezone.utc)
    data.pop("published", None)

    for key, value in data.items():
        setattr(post, key, value)

    await db.flush()
    await db.refresh(post)  # load onupdate updated_at before serialization
    await log_admin_action(
        db,
        admin.id,
        "blog_post_updated",
        details={"post_id": str(post.id), "slug": post.slug, "published": post.published},
    )
    return post


@router.delete("/admin/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_post(
    post_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a blog post (admin-only). Audit-logged."""
    post = await _get_post_or_404(db, post_id)
    slug = post.slug
    await db.delete(post)
    await db.flush()
    await log_admin_action(
        db,
        admin.id,
        "blog_post_deleted",
        details={"post_id": str(post_id), "slug": slug},
    )
    return None
