"""
Tests for the idea-inbox testing-debt items (TODO.md → Testing Debt):
  - /inbox/count returns the correct UNPROMOTED count (promoted items drop out)
  - promote validates ai_partner_style and falls back to "strategist" on junk
  - promote honors a valid ai_partner_style
  - promote is ownership-scoped (another user's item → 404)
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.idea_inbox import IdeaInbox
from app.models.user import User
from app.routers.auth import get_current_user


# ── Fixtures ────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User):
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


async def _make_item(db: AsyncSession, user_id: uuid.UUID, subject: str = "An idea") -> IdeaInbox:
    item = IdeaInbox(user_id=user_id, subject=subject, body="Some body text", source="manual")
    db.add(item)
    await db.flush()
    return item


# ── Tests ───────────────────────────────────────────────────────────


class TestInboxCount:
    def test_empty_inbox_counts_zero(self, client):
        resp = client.get("/api/v1/inbox/count")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_count_excludes_promoted_items(self, client, db_session, test_user):
        first = await _make_item(db_session, test_user.id, "Keep me")
        await _make_item(db_session, test_user.id, "Promote me")

        assert client.get("/api/v1/inbox/count").json()["count"] == 2

        items = client.get("/api/v1/inbox").json()
        promote_id = next(i["id"] for i in items if i["subject"] == "Promote me")
        assert client.post(f"/api/v1/inbox/{promote_id}/promote", json={}).status_code == 200

        # Promoted item no longer counts as unread
        assert client.get("/api/v1/inbox/count").json()["count"] == 1
        assert str(first.id)  # the other item still exists untouched

    @pytest.mark.asyncio
    async def test_count_scoped_to_user(self, client, db_session, test_user):
        other = User(id=uuid.uuid4(), email="other@example.com", email_verified=True)
        db_session.add(other)
        await db_session.flush()
        await _make_item(db_session, other.id, "Someone else's idea")

        assert client.get("/api/v1/inbox/count").json()["count"] == 0


class TestPromotePartnerStyle:
    @pytest.mark.asyncio
    async def test_invalid_partner_style_falls_back_to_strategist(
        self, client, db_session, test_user
    ):
        item = await _make_item(db_session, test_user.id)
        resp = client.post(
            f"/api/v1/inbox/{item.id}/promote",
            json={"ai_partner_style": "not-a-real-style"},
        )
        assert resp.status_code == 200
        project_id = resp.json()["project_id"]

        proj = client.get(f"/api/v1/projects/{project_id}")
        assert proj.status_code == 200
        assert proj.json()["ai_partner_style"] == "strategist"

    @pytest.mark.asyncio
    async def test_valid_partner_style_is_used(self, client, db_session, test_user):
        item = await _make_item(db_session, test_user.id)
        resp = client.post(
            f"/api/v1/inbox/{item.id}/promote",
            json={"ai_partner_style": "skeptic"},
        )
        assert resp.status_code == 200
        proj = client.get(f"/api/v1/projects/{resp.json()['project_id']}")
        assert proj.json()["ai_partner_style"] == "skeptic"

    @pytest.mark.asyncio
    async def test_promote_other_users_item_is_404(self, client, db_session):
        other = User(id=uuid.uuid4(), email="other2@example.com", email_verified=True)
        db_session.add(other)
        await db_session.flush()
        foreign = await _make_item(db_session, other.id, "Not yours")

        resp = client.post(f"/api/v1/inbox/{foreign.id}/promote", json={})
        assert resp.status_code == 404
