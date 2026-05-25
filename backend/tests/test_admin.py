"""
Integration tests for the /admin API surface.

Covers:
  - require_admin gate (403 for non-admins)
  - User list (pagination, search, plan filter)
  - User detail (usage counts, effective limits)
  - Plan update + audit log creation
  - Entitlement override merge into effective limits
  - Admin flag grant/revoke + self-revoke block
  - Audit log list with filters
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.models.admin_audit_log import AdminAuditLog
from app.models.user import User
from app.routers.auth import get_current_user


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


class TestRequireAdmin:

    def test_non_admin_gets_403(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/users")
        assert resp.status_code == 403
        assert "Admin access required" in resp.json()["detail"]

    def test_non_admin_cannot_update_plan(self, nonadmin_client, admin_user):
        resp = nonadmin_client.patch(
            f"/api/v1/admin/users/{admin_user.id}/plan",
            json={"account_type": "basic"},
        )
        assert resp.status_code == 403

    def test_non_admin_cannot_view_audit_log(self, nonadmin_client):
        resp = nonadmin_client.get("/api/v1/admin/audit-log")
        assert resp.status_code == 403


class TestUserList:

    def test_list_returns_both_users(self, admin_client, admin_user, regular_user):
        resp = admin_client.get("/api/v1/admin/users")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_search_filters_by_email(self, admin_client, admin_user, regular_user):
        resp = admin_client.get("/api/v1/admin/users?search=regular")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "regular@example.com"

    def test_plan_filter(self, admin_client, admin_user, regular_user):
        resp = admin_client.get("/api/v1/admin/users?plan=free")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["account_type"] == "free"

    def test_pagination(self, admin_client, admin_user, regular_user):
        resp = admin_client.get("/api/v1/admin/users?per_page=1&page=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["page"] == 1


class TestUserDetail:

    def test_get_user_detail(self, admin_client, regular_user):
        resp = admin_client.get(f"/api/v1/admin/users/{regular_user.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "regular@example.com"
        assert data["account_type"] == "free"
        assert data["project_count"] == 0
        assert "effective_limits" in data
        assert data["effective_limits"]["projects"] == 3

    def test_get_nonexistent_user_404(self, admin_client):
        fake_id = uuid.uuid4()
        resp = admin_client.get(f"/api/v1/admin/users/{fake_id}")
        assert resp.status_code == 404


class TestPlanUpdate:

    def test_update_plan_changes_account_type(self, admin_client, regular_user, db_session):
        resp = admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "pro"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_type"] == "pro"
        assert data["effective_limits"]["projects"] is None

    def test_update_plan_creates_audit_log(self, admin_client, admin_user, regular_user, db_session):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "basic"},
        )

        import asyncio
        async def _check():
            result = await db_session.execute(
                select(AdminAuditLog).where(
                    AdminAuditLog.target_user_id == regular_user.id,
                    AdminAuditLog.action == "plan_changed",
                )
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.admin_user_id == admin_user.id
            assert entry.details["from"] == "free"
            assert entry.details["to"] == "basic"

        asyncio.get_event_loop().run_until_complete(_check())

    def test_same_plan_logs_unchanged(self, admin_client, regular_user, db_session):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "free"},
        )

        import asyncio
        async def _check():
            result = await db_session.execute(
                select(AdminAuditLog).where(
                    AdminAuditLog.target_user_id == regular_user.id,
                    AdminAuditLog.action == "plan_unchanged",
                )
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.details["plan"] == "free"

        asyncio.get_event_loop().run_until_complete(_check())

    def test_invalid_plan_rejected(self, admin_client, regular_user):
        resp = admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "enterprise"},
        )
        assert resp.status_code == 422


class TestEntitlementOverrides:

    def test_set_overrides_reflected_in_effective_limits(self, admin_client, regular_user):
        resp = admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/overrides",
            json={"entitlement_overrides": {"projects": 100}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["effective_limits"]["projects"] == 100
        assert data["effective_limits"]["prompt_packages"] == 0

    def test_null_override_means_unlimited(self, admin_client, regular_user):
        resp = admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/overrides",
            json={"entitlement_overrides": {"projects": None}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["effective_limits"]["projects"] is None

    def test_clear_overrides(self, admin_client, regular_user):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/overrides",
            json={"entitlement_overrides": {"projects": 999}},
        )
        resp = admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/overrides",
            json={"entitlement_overrides": None},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["effective_limits"]["projects"] == 3

    def test_override_creates_audit_log(self, admin_client, admin_user, regular_user, db_session):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/overrides",
            json={"entitlement_overrides": {"projects": 50}},
        )

        import asyncio
        async def _check():
            result = await db_session.execute(
                select(AdminAuditLog).where(
                    AdminAuditLog.target_user_id == regular_user.id,
                    AdminAuditLog.action == "overrides_updated",
                )
            )
            entry = result.scalar_one_or_none()
            assert entry is not None
            assert entry.details["after"]["projects"] == 50

        asyncio.get_event_loop().run_until_complete(_check())


class TestAdminFlag:

    def test_grant_admin(self, admin_client, regular_user):
        resp = admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/admin",
            json={"is_admin": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True

    def test_revoke_admin_on_other_user(self, admin_client, regular_user, db_session):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/admin",
            json={"is_admin": True},
        )
        resp = admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/admin",
            json={"is_admin": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is False

    def test_self_revoke_blocked(self, admin_client, admin_user):
        resp = admin_client.patch(
            f"/api/v1/admin/users/{admin_user.id}/admin",
            json={"is_admin": False},
        )
        assert resp.status_code == 400
        assert "cannot revoke your own" in resp.json()["detail"]

    def test_self_grant_is_noop_not_error(self, admin_client, admin_user):
        resp = admin_client.patch(
            f"/api/v1/admin/users/{admin_user.id}/admin",
            json={"is_admin": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_admin"] is True

    def test_grant_creates_audit_log(self, admin_client, admin_user, regular_user, db_session):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/admin",
            json={"is_admin": True},
        )

        import asyncio
        async def _check():
            result = await db_session.execute(
                select(AdminAuditLog).where(
                    AdminAuditLog.target_user_id == regular_user.id,
                    AdminAuditLog.action == "admin_granted",
                )
            )
            assert result.scalar_one_or_none() is not None

        asyncio.get_event_loop().run_until_complete(_check())


class TestAuditLog:

    def test_empty_audit_log(self, admin_client):
        resp = admin_client.get("/api/v1/admin/audit-log")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_audit_log_after_plan_change(self, admin_client, regular_user):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "basic"},
        )
        resp = admin_client.get("/api/v1/admin/audit-log")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        actions = [item["action"] for item in data["items"]]
        assert "plan_changed" in actions

    def test_audit_log_filter_by_action(self, admin_client, regular_user):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "basic"},
        )
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/admin",
            json={"is_admin": True},
        )
        resp = admin_client.get("/api/v1/admin/audit-log?action=plan_changed")
        data = resp.json()
        assert all(item["action"] == "plan_changed" for item in data["items"])

    def test_audit_log_filter_by_target(self, admin_client, admin_user, regular_user):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "basic"},
        )
        resp = admin_client.get(
            f"/api/v1/admin/audit-log?target_user_id={regular_user.id}"
        )
        data = resp.json()
        assert data["total"] >= 1
        assert all(
            item["target_user_id"] == str(regular_user.id) for item in data["items"]
        )

    def test_audit_log_includes_emails(self, admin_client, admin_user, regular_user):
        admin_client.patch(
            f"/api/v1/admin/users/{regular_user.id}/plan",
            json={"account_type": "pro"},
        )
        resp = admin_client.get("/api/v1/admin/audit-log")
        data = resp.json()
        entry = data["items"][0]
        assert entry["admin_email"] == "admin@example.com"
        assert entry["target_email"] == "regular@example.com"
