"""
Integration tests for the /blog API surface.

Covers:
  - Public list (published only, hides drafts) + single fetch by slug
  - View-count increment on public read
  - 404s for drafts / missing slugs
  - require_admin gate (403 for non-admins) on every admin route
  - Admin create (draft + published), slug derivation, custom slug, duplicate 409
  - Admin list incl. drafts + status filter
  - Admin update (publish transition sets published_at), slug dedup, body edit
  - Admin delete
  - Audit-log entries for create
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.blog_post import BlogPost
from app.models.user import User
from app.routers.auth import get_current_user


# ── Fixtures ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="admin@example.com",
        name="Admin User",
        display_name="Admin",
        email_verified=True,
        account_type="pro",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email="regular@example.com",
        name="Regular User",
        display_name="Regular",
        email_verified=True,
        account_type="free",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def published_post(db_session: AsyncSession, admin_user: User) -> BlogPost:
    post = BlogPost(
        title="Getting Started with Ide/AI",
        slug="getting-started",
        excerpt="Turn an idea into a design kit.",
        body="# Hello\n\nWelcome to Ide/AI.",
        published=True,
        published_at=datetime.now(timezone.utc),
        created_by=admin_user.id,
        view_count=0,
    )
    db_session.add(post)
    await db_session.flush()
    return post


@pytest_asyncio.fixture
async def draft_post(db_session: AsyncSession, admin_user: User) -> BlogPost:
    post = BlogPost(
        title="Secret Draft",
        slug="secret-draft",
        body="work in progress",
        published=False,
        created_by=admin_user.id,
        view_count=0,
    )
    db_session.add(post)
    await db_session.flush()
    return post


@pytest_asyncio.fixture
async def public_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db_session: AsyncSession, admin_user: User):
    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return admin_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def nonadmin_client(db_session: AsyncSession, regular_user: User):
    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return regular_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Public reads ────────────────────────────────────────────────────


class TestPublicReads:

    def test_list_empty(self, public_client):
        resp = public_client.get("/api/v1/blog/posts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_shows_published(self, public_client, published_post):
        resp = public_client.get("/api/v1/blog/posts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["slug"] == "getting-started"
        assert "body" not in data[0]  # summary omits body

    def test_list_hides_drafts(self, public_client, draft_post):
        resp = public_client.get("/api/v1/blog/posts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_published_by_slug(self, public_client, published_post):
        resp = public_client.get("/api/v1/blog/posts/getting-started")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "getting-started"
        assert data["body"].startswith("# Hello")

    def test_get_increments_view_count(self, public_client, published_post):
        first = public_client.get("/api/v1/blog/posts/getting-started")
        assert first.json()["view_count"] == 1
        second = public_client.get("/api/v1/blog/posts/getting-started")
        assert second.json()["view_count"] == 2

    def test_get_draft_by_slug_404(self, public_client, draft_post):
        resp = public_client.get("/api/v1/blog/posts/secret-draft")
        assert resp.status_code == 404

    def test_get_missing_slug_404(self, public_client):
        resp = public_client.get("/api/v1/blog/posts/does-not-exist")
        assert resp.status_code == 404


# ── Admin gate ──────────────────────────────────────────────────────


class TestAdminGate:

    def test_non_admin_cannot_list(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/blog/admin/posts")
        assert resp.status_code == 403

    def test_non_admin_cannot_create(self, nonadmin_client):
        resp = nonadmin_client.post(
            "/api/v1/blog/admin/posts", json={"title": "Nope", "body": "x"}
        )
        assert resp.status_code == 403


# ── Admin create ────────────────────────────────────────────────────


class TestAdminCreate:

    def test_create_draft_defaults(self, admin_client):
        resp = admin_client.post(
            "/api/v1/blog/admin/posts", json={"title": "My First Post", "body": "Hello world"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["slug"] == "my-first-post"
        assert data["published"] is False
        assert data["published_at"] is None
        assert data["view_count"] == 0

    def test_create_published_sets_published_at(self, admin_client):
        resp = admin_client.post(
            "/api/v1/blog/admin/posts",
            json={"title": "Live Post", "body": "content", "published": True},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["published"] is True
        assert data["published_at"] is not None

    def test_create_custom_slug_is_slugified(self, admin_client):
        resp = admin_client.post(
            "/api/v1/blog/admin/posts",
            json={"title": "Anything", "body": "x", "slug": "Custom Slug!!"},
        )
        assert resp.status_code == 201
        assert resp.json()["slug"] == "custom-slug"

    def test_duplicate_slug_409(self, admin_client):
        admin_client.post("/api/v1/blog/admin/posts", json={"title": "Dup", "body": "x"})
        resp = admin_client.post("/api/v1/blog/admin/posts", json={"title": "Dup", "body": "y"})
        assert resp.status_code == 409

    def test_create_writes_audit_log(self, admin_client):
        admin_client.post("/api/v1/blog/admin/posts", json={"title": "Audited", "body": "x"})
        resp = admin_client.get("/api/v1/admin/audit-log?action=blog_post_created")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1


# ── Admin list / detail ─────────────────────────────────────────────


class TestAdminList:

    def test_list_includes_drafts(self, admin_client, published_post, draft_post):
        resp = admin_client.get("/api/v1/blog/admin/posts")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_status_filter_draft(self, admin_client, published_post, draft_post):
        resp = admin_client.get("/api/v1/blog/admin/posts?status=draft")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "secret-draft"

    def test_status_filter_published(self, admin_client, published_post, draft_post):
        resp = admin_client.get("/api/v1/blog/admin/posts?status=published")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["slug"] == "getting-started"

    def test_get_draft_by_id(self, admin_client, draft_post):
        resp = admin_client.get(f"/api/v1/blog/admin/posts/{draft_post.id}")
        assert resp.status_code == 200
        assert resp.json()["slug"] == "secret-draft"


# ── Admin update / delete ───────────────────────────────────────────


class TestAdminUpdate:

    def test_publish_transition_sets_published_at(self, admin_client, draft_post):
        resp = admin_client.patch(
            f"/api/v1/blog/admin/posts/{draft_post.id}", json={"published": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["published"] is True
        assert data["published_at"] is not None

    def test_update_body(self, admin_client, draft_post):
        resp = admin_client.patch(
            f"/api/v1/blog/admin/posts/{draft_post.id}", json={"body": "rewritten"}
        )
        assert resp.status_code == 200
        assert resp.json()["body"] == "rewritten"

    def test_update_slug_collision_409(self, admin_client, published_post):
        created = admin_client.post(
            "/api/v1/blog/admin/posts", json={"title": "Another", "body": "x"}
        ).json()
        resp = admin_client.patch(
            f"/api/v1/blog/admin/posts/{created['id']}", json={"slug": "getting-started"}
        )
        assert resp.status_code == 409

    def test_update_missing_404(self, admin_client):
        resp = admin_client.patch(
            f"/api/v1/blog/admin/posts/{uuid.uuid4()}", json={"body": "x"}
        )
        assert resp.status_code == 404


class TestAdminDelete:

    def test_delete_then_404(self, admin_client, published_post):
        resp = admin_client.delete(f"/api/v1/blog/admin/posts/{published_post.id}")
        assert resp.status_code == 204
        follow = admin_client.get(f"/api/v1/blog/admin/posts/{published_post.id}")
        assert follow.status_code == 404
