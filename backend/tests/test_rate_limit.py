"""
Regression tests for per-IP rate limiting on public endpoints (SAST-H1).

The suite-wide conftest sets RATE_LIMIT_ENABLED=false so the rest of the
tests never trip a limiter; these tests flip ``limiter.enabled`` back on
(and reset its counters) around each case to prove:
  - exceeding the per-minute limit on anonymous POST endpoints returns 429
  - the limit keys on client IP (X-Forwarded-For aware), so a different
    client is not blocked by another client's exhaustion
  - the limiter stays inert when disabled (the suite default)
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.main import app
from app.models.project import Project
from app.models.project_share import ProjectShare
from app.models.user import User


# ── Fixtures ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def shared_project(db_session: AsyncSession, test_user: User) -> ProjectShare:
    project = Project(user_id=test_user.id, name="Rate Limit Test Project")
    db_session.add(project)
    await db_session.flush()
    share = ProjectShare(
        project_id=project.id,
        share_token=uuid.uuid4().hex,
        is_public=True,
        created_by=test_user.id,
        allow_feedback=True,
        allow_ratings=True,
    )
    db_session.add(share)
    await db_session.flush()
    return share


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def limiter_on():
    """Enable the (suite-disabled) limiter with fresh counters, then restore."""
    limiter.reset()
    limiter.enabled = True
    yield limiter
    limiter.enabled = False
    limiter.reset()


COMMENT = {"author_name": "Visitor", "content": "Nice project!"}


# ── Tests ───────────────────────────────────────────────────────────


class TestRateLimitDisabled:
    def test_suite_default_is_disabled(self):
        # conftest sets RATE_LIMIT_ENABLED=false before app import
        assert limiter.enabled is False

    def test_no_429_when_disabled(self, client, shared_project):
        for _ in range(15):  # over the 10/minute limit
            resp = client.post(
                f"/api/v1/sharing/public/{shared_project.share_token}/comments",
                json=COMMENT,
            )
            assert resp.status_code == 201


class TestRateLimit429:
    def test_comment_spam_hits_429(self, client, shared_project, limiter_on):
        url = f"/api/v1/sharing/public/{shared_project.share_token}/comments"
        for i in range(10):
            assert client.post(url, json=COMMENT).status_code == 201, f"request {i}"
        resp = client.post(url, json=COMMENT)
        assert resp.status_code == 429

    def test_rating_spam_hits_429(self, client, shared_project, limiter_on):
        url = f"/api/v1/sharing/public/{shared_project.share_token}/ratings"
        for _ in range(10):
            assert client.post(url, json={"score": 5}).status_code == 201
        assert client.post(url, json={"score": 5}).status_code == 429

    def test_password_verify_brute_force_hits_429(self, client, shared_project, limiter_on):
        url = f"/api/v1/sharing/public/{shared_project.share_token}/verify"
        # Share has no password → endpoint returns data (200); the limiter
        # fires on request count regardless of outcome, which is the point
        # for brute-force protection.
        for _ in range(10):
            assert client.post(url, json={"password": "guess"}).status_code == 200
        assert client.post(url, json={"password": "guess"}).status_code == 429


class TestRateLimitKeying:
    def test_different_forwarded_ip_not_blocked(self, client, shared_project, limiter_on):
        """Exhausting the limit as one client must not block another."""
        url = f"/api/v1/sharing/public/{shared_project.share_token}/comments"
        attacker = {"X-Forwarded-For": "203.0.113.7"}
        for _ in range(10):
            assert client.post(url, json=COMMENT, headers=attacker).status_code == 201
        assert client.post(url, json=COMMENT, headers=attacker).status_code == 429
        # A different client IP still gets through
        other = {"X-Forwarded-For": "198.51.100.42"}
        assert client.post(url, json=COMMENT, headers=other).status_code == 201

    def test_first_xff_hop_is_used(self, client, shared_project, limiter_on):
        """Key is the FIRST X-Forwarded-For entry (the real client, per Railway)."""
        url = f"/api/v1/sharing/public/{shared_project.share_token}/comments"
        for _ in range(10):
            assert (
                client.post(
                    url, json=COMMENT,
                    headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"},
                ).status_code
                == 201
            )
        # Same client IP, different proxy hop — still the same bucket → 429
        resp = client.post(
            url, json=COMMENT,
            headers={"X-Forwarded-For": "203.0.113.7, 10.9.9.9"},
        )
        assert resp.status_code == 429
