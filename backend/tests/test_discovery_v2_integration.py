"""
HTTP-level integration tests for Discovery v2 routes.

Uses FastAPI's TestClient with dependency overrides for ``get_db`` (uses the
in-memory SQLite session) and ``get_current_user`` (returns the test_user
fixture). The Anthropic client is monkeypatched per-test where AI calls are
expected — non-AI routes don't need it.

Covers Phase 1-4 + audit-closure HTTP-route behavior that the service-layer
tests in ``test_discovery_v2.py`` can't reach:

  - **H1**: POST /projects downgrades flow_version to v1 when up-front pathway
    assembly is skipped (no primary_category, empty assembly, or exception).
  - **M6**: GET /discovery/{session_id}/field-summary returns 200 + summary
    for v2 projects, 409 for v1, 404 for missing or other-user sessions.
  - **Phase 3 hotfix**: POST /templates/{id}/use creates flow_version='v1'.
  - **Phase 1**: POST /projects with primary_category creates a ModulePathway
    row with the expected module-id strings.

PostgreSQL ON CONFLICT upsert is still out of scope (SQLite harness). SSE
streaming endpoints (init / message) are not exercised here — that would
require mocking the AsyncAnthropic streaming client and is deferred.
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
from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.project import Project
from app.models.project_template import ProjectTemplate
from app.models.session import DiscoverySession
from app.models.user import User
from app.routers.auth import get_current_user
from app.services import discovery_service


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User):
    """FastAPI TestClient with dep overrides for db + auth.

    Both deps are overridden to point at the test fixtures. The yield-after-cleanup
    pattern ensures other tests don't inherit our overrides.
    """
    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    yield TestClient(app)

    app.dependency_overrides.clear()


# ── 1. POST /projects (H1) ───────────────────────────────────────────────


class TestCreateProjectH1:
    """Verifies the H1 fix: orphan v2 projects get downgraded to v1."""

    def test_creates_v2_with_pathway_when_category_set(self, client, db_session):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "v2 Happy Path",
                "description": "A v2 project with a category",
                "platform": "web",
                "audience": "consumers",
                "complexity": "medium",
                "tone": "casual",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["flow_version"] == "v2"
        assert body["primary_category"] == "software_tech"

        # Pathway row should have been created with module-id strings
        project_id = body["id"]
        result = client.get(f"/api/v1/projects/{project_id}")
        assert result.status_code == 200

    def test_downgrades_to_v1_when_no_primary_category(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Orphan v2 → v1",
                "description": "Project with no primary_category",
                "platform": "custom",
                "audience": "consumers",
                "complexity": "simple",
                "tone": "casual",
                # primary_category intentionally omitted
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        # H1 fix: would have been v2 (server default) but the assembly skip
        # downgrades it.
        assert body["flow_version"] == "v1", (
            "H1: project without primary_category must be downgraded to v1 — "
            f"got flow_version={body['flow_version']}"
        )

    def test_downgrades_to_v1_when_assembly_returns_empty(
        self, client, monkeypatch
    ):
        # Force the assembler to return zero modules
        from app.services import modular_pathway_service

        def fake_assemble(**kwargs):
            return {"modules": [], "primary_category": kwargs.get("primary_category"), "secondary_category": None}

        monkeypatch.setattr(
            modular_pathway_service,
            "assemble_pathway_from_creation_inputs",
            fake_assemble,
        )

        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Empty Assembly → v1",
                "description": "Mocked assembly returns []",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["flow_version"] == "v1"

    def test_downgrades_to_v1_when_assembly_raises(self, client, monkeypatch):
        from app.services import modular_pathway_service

        def boom(**kwargs):
            raise RuntimeError("simulated assembly failure")

        monkeypatch.setattr(
            modular_pathway_service,
            "assemble_pathway_from_creation_inputs",
            boom,
        )

        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Assembly Crash → v1",
                "description": "Mocked assembly raises",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["flow_version"] == "v1"

    @pytest.mark.asyncio
    async def test_pathway_row_uses_string_ids(self, client, db_session):
        """Phase 2 hotfix invariant: module_pathways.modules is list[str]."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Shape check",
                "description": "Pathway must store IDs as strings",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201
        project_id = uuid.UUID(resp.json()["id"])

        result = await db_session.execute(
            select(ModulePathway).where(ModulePathway.project_id == project_id)
        )
        pathway = result.scalar_one_or_none()
        assert pathway is not None, "v2 project with category should have a pathway"
        assert pathway.modules, "pathway should have ≥1 module"
        assert all(isinstance(m, str) for m in pathway.modules), (
            f"all module entries must be strings, got: {[type(m).__name__ for m in pathway.modules]}"
        )


# ── 2. GET /discovery/{session_id}/field-summary (M6) ────────────────────


class TestFieldSummaryEndpoint:
    """Verifies the M6 endpoint added in audit closure."""

    @pytest.mark.asyncio
    async def test_returns_summary_for_v2(self, client, db_session, test_user):
        # Create a v2 project via the HTTP route
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Field summary v2",
                "description": "Test project",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        # Start a session
        resp = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id},
        )
        assert resp.status_code == 201, resp.text
        session_id = resp.json()["id"]

        # Fetch the field summary
        resp = client.get(f"/api/v1/discovery/{session_id}/field-summary")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Shape assertions
        for key in (
            "total_filled", "total_fields", "required_filled",
            "required_total", "overall_percent", "per_module",
        ):
            assert key in body, f"missing key {key} in field-summary response"
        # No responses yet → all filled counts are zero
        assert body["total_filled"] == 0
        assert body["required_filled"] == 0
        # But denominators populated from the seeded pathway
        assert body["total_fields"] > 0
        assert body["required_total"] > 0
        assert body["overall_percent"] == 0
        assert isinstance(body["per_module"], list) and len(body["per_module"]) > 0

    def test_returns_409_for_v1_project(self, client):
        # Create a v1 project (no primary_category → H1 downgrades it)
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Field summary v1",
                "description": "Test",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["flow_version"] == "v1"
        project_id = resp.json()["id"]

        resp = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id},
        )
        assert resp.status_code == 201
        session_id = resp.json()["id"]

        resp = client.get(f"/api/v1/discovery/{session_id}/field-summary")
        assert resp.status_code == 409, resp.text
        assert "v1" in resp.json()["detail"].lower()

    def test_returns_404_for_nonexistent_session(self, client):
        random_id = str(uuid.uuid4())
        resp = client.get(f"/api/v1/discovery/{random_id}/field-summary")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_for_other_users_session(
        self, client, db_session, test_user
    ):
        """Cross-user isolation — session belongs to a DIFFERENT user."""
        # Create a project + session owned by an OTHER user, then attempt to
        # read its summary while the auth override returns test_user.
        other_user = User(
            id=uuid.uuid4(),
            email=f"other-{uuid.uuid4().hex[:8]}@example.com",
            name="Other",
            display_name="Other",
            email_verified=True,
            account_type="free",
        )
        db_session.add(other_user)
        await db_session.flush()

        other_project = Project(
            id=uuid.uuid4(),
            user_id=other_user.id,
            name="Other's project",
            description="not ours",
            primary_category="software_tech",
            flow_version="v2",
        )
        db_session.add(other_project)
        await db_session.flush()

        other_session = DiscoverySession(
            id=uuid.uuid4(),
            project_id=other_project.id,
            stage="greeting",
            status="active",
            messages=[],
            ai_partner_style="strategist",
        )
        db_session.add(other_session)
        await db_session.commit()

        resp = client.get(f"/api/v1/discovery/{other_session.id}/field-summary")
        assert resp.status_code == 404, (
            "cross-user request must 404, not leak summary data"
        )


# ── 3. POST /templates/{id}/use (Phase 3 hotfix) ─────────────────────────


class TestTemplateFlowVersion:
    """Phase 3 hotfix invariant: template-created projects are flow_version=v1."""

    @pytest.mark.asyncio
    async def test_template_project_is_v1(self, client, db_session):
        # Seed a template
        template = ProjectTemplate(
            id=uuid.uuid4(),
            name="Test Template",
            description="A test template",
            icon="🧪",
            category="software_tech",
            concept_sheet={"problem": "x", "audience": "y", "mvp": "z"},
            is_system=True,
        )
        db_session.add(template)
        await db_session.commit()

        resp = client.post(
            f"/api/v1/templates/{template.id}/use",
            json={"ai_partner_style": "strategist"},
        )
        assert resp.status_code == 200, resp.text
        project_id = resp.json()["project_id"]

        result = await db_session.execute(
            select(Project).where(Project.id == uuid.UUID(project_id))
        )
        project = result.scalar_one()
        assert project.flow_version == "v1", (
            "Phase 3 hotfix: template-created projects must be v1 (they don't "
            "go through up-front pathway assembly). Got: "
            f"flow_version={project.flow_version}"
        )


# ── 4. Library resume routing (Phase 3 hotfix + Phase 4 v2 routing) ──────


class TestLibraryResumeRouting:
    """Verifies _compute_resume_path branches on flow_version."""

    def test_v2_in_progress_resumes_to_discovery(self):
        from app.routers.library import _compute_resume_path
        pid = uuid.uuid4()

        # In-progress v2 projects route to /discovery
        for session_status in ("active", None):
            for pathway_status in (None, "pending", "active"):
                path = _compute_resume_path(
                    pid,
                    session_status=session_status,
                    discovery_stage="greeting",
                    block_count=0,
                    pathway_status=pathway_status,
                    flow_version="v2",
                )
                assert path == f"/discovery/{pid}", (
                    f"in-progress v2 routes to /discovery — got {path} for "
                    f"session={session_status} pathway={pathway_status}"
                )

    def test_v2_completed_resumes_to_design_kit(self):
        from app.routers.library import _compute_resume_path
        pid = uuid.uuid4()

        # Completed session → /design-kit
        path = _compute_resume_path(
            pid, session_status="completed", discovery_stage="confirm",
            block_count=0, pathway_status="active", flow_version="v2",
        )
        assert path == f"/design-kit/{pid}"

        # Pathway complete → /design-kit
        path = _compute_resume_path(
            pid, session_status="active", discovery_stage="greeting",
            block_count=0, pathway_status="complete", flow_version="v2",
        )
        assert path == f"/design-kit/{pid}"

    def test_v1_routing_unchanged(self):
        from app.routers.library import _compute_resume_path
        pid = uuid.uuid4()

        # Mid-discovery → /discovery
        assert _compute_resume_path(pid, "active", "greeting", 0, None, "v1") == f"/discovery/{pid}"
        # Discovery done, no pathway → /pathway-review
        assert _compute_resume_path(pid, "completed", "confirm", 0, None, "v1") == f"/pathway-review/{pid}"
        # Discovery done, pathway pending → /pathway-review
        assert _compute_resume_path(pid, "completed", "confirm", 0, "pending", "v1") == f"/pathway-review/{pid}"
        # Discovery done, pathway active → /pathway-execute
        assert _compute_resume_path(pid, "completed", "confirm", 0, "active", "v1") == f"/pathway-execute/{pid}"
        # Pathway complete, no blocks → /blocks
        assert _compute_resume_path(pid, "completed", "confirm", 0, "complete", "v1") == f"/blocks/{pid}"
        # Pathway complete, has blocks → /exports
        assert _compute_resume_path(pid, "completed", "confirm", 5, "complete", "v1") == f"/exports/{pid}"


# ── 5. Discovery session-start + project ownership ───────────────────────


class TestDiscoveryStartV2:
    """Sanity check: POST /discovery/start for a v2 project sets up the
    session with the correct partner style and returns it via GET."""

    def test_start_creates_session_for_v2(self, client):
        # Create v2 project
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Start v2",
                "description": "Test",
                "primary_category": "software_tech",
                "ai_partner_style": "skeptic",
            },
        )
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        # Start session
        resp = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["ai_partner_style"] == "skeptic"
        assert body["project_id"] == project_id

    def test_start_rejects_unauthorized_project(self, client, db_session, test_user):
        """Starting a session on someone else's project must 404."""
        # Create a v2 project owned by the test_user
        other_user_id = uuid.uuid4()
        other_proj_resp = client.post(
            "/api/v1/projects",
            json={"name": "owner's project", "primary_category": "software_tech",
                  "ai_partner_style": "strategist"},
        )
        project_id = other_proj_resp.json()["id"]

        # Now flip the auth override to a different user
        from app.routers.auth import get_current_user as _gcu
        original = app.dependency_overrides.get(_gcu)
        def alt_user():
            return User(
                id=other_user_id,
                email="someone-else@example.com",
                name="Someone Else",
                display_name="Else",
                email_verified=True,
                account_type="free",
            )
        app.dependency_overrides[_gcu] = alt_user
        try:
            resp = client.post(
                "/api/v1/discovery/start",
                json={"project_id": project_id},
            )
            assert resp.status_code == 404
        finally:
            if original:
                app.dependency_overrides[_gcu] = original


# ── 6. Project response shape ────────────────────────────────────────────


class TestProjectReadShape:
    """Verifies ProjectRead schema returns all the fields Phase 4 frontend
    relies on (flow_version, primary_category, secondary_category,
    pathway_locked) — and they have the expected types."""

    def test_v2_project_response_shape(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Shape test",
                "description": "Verify v2 response shape",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        # All fields the frontend Project type expects:
        for key in (
            "id", "user_id", "name", "description", "platform", "audience",
            "complexity", "tone", "accent_color", "pathway_id",
            "ai_partner_style", "primary_category", "secondary_category",
            "pathway_locked", "flow_version", "created_at", "updated_at",
        ):
            assert key in body, f"missing {key} in ProjectRead response"
        assert body["flow_version"] == "v2"
        assert body["primary_category"] == "software_tech"
        assert isinstance(body["pathway_locked"], bool)


# ── 7. Design Kit endpoint ──────────────────────────────────────────────


class TestDesignKitEndpoint:
    """Verifies GET /projects/{project_id}/design-kit and
    PATCH /modules/{project_id}/{module_id}/responses."""

    def test_design_kit_returns_modules_with_fields(self, client):
        # Create a v2 project (triggers pathway assembly)
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Design Kit Test",
                "description": "Test the design-kit endpoint",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        resp = client.get(f"/api/v1/projects/{project_id}/design-kit")
        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == project_id
        assert body["project_name"] == "Design Kit Test"
        assert isinstance(body["modules"], list)
        assert len(body["modules"]) > 0

        # Each module has expected shape
        mod = body["modules"][0]
        for key in ("module_id", "label", "description", "group", "has_output", "fields", "responses", "status"):
            assert key in mod, f"missing {key} in design-kit module"
        assert isinstance(mod["fields"], list)
        assert isinstance(mod["responses"], dict)

    def test_design_kit_rejects_v1_project(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={"name": "v1 project", "description": "no category"},
        )
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        resp = client.get(f"/api/v1/projects/{project_id}/design-kit")
        assert resp.status_code == 409

    def test_patch_module_responses_validates_keys(self, client):
        # Create v2 project
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "PATCH Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Get first module from design-kit to know a valid module_id
        kit_resp = client.get(f"/api/v1/projects/{project_id}/design-kit")
        first_module = kit_resp.json()["modules"][0]
        module_id = first_module["module_id"]
        valid_key = first_module["fields"][0]["key"]

        # PATCH with valid field
        resp = client.patch(
            f"/api/v1/modules/{project_id}/{module_id}/responses",
            json={valid_key: "test value"},
        )
        assert resp.status_code == 200
        assert resp.json()["responses"][valid_key] == "test value"
        assert resp.json()["module_id"] == module_id

    def test_patch_module_responses_rejects_unknown_keys(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "PATCH Reject Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        kit_resp = client.get(f"/api/v1/projects/{project_id}/design-kit")
        module_id = kit_resp.json()["modules"][0]["module_id"]

        resp = client.patch(
            f"/api/v1/modules/{project_id}/{module_id}/responses",
            json={"completely_fake_key_xyz": "value"},
        )
        assert resp.status_code == 422
        assert "Unknown field keys" in resp.json()["detail"]

    def test_patch_module_responses_rejects_unknown_module(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "PATCH Unknown Module",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        resp = client.patch(
            f"/api/v1/modules/{project_id}/fake_module_xyz/responses",
            json={"field": "value"},
        )
        assert resp.status_code == 404


class TestRefreshOutput:
    """Tests for POST /modules/{project_id}/{module_id}/refresh-output."""

    def test_refresh_output_rejects_non_has_output_module(self, client):
        """Modules without has_output: true should return 400."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Refresh Reject",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Find a module that does NOT have has_output
        kit_resp = client.get(f"/api/v1/projects/{project_id}/design-kit")
        modules = kit_resp.json()["modules"]
        non_output_mod = next((m for m in modules if not m["has_output"]), None)
        assert non_output_mod is not None, "Should have at least one non-has_output module"

        resp = client.post(
            f"/api/v1/modules/{project_id}/{non_output_mod['module_id']}/refresh-output",
        )
        assert resp.status_code == 400
        assert "does not support output generation" in resp.json()["detail"]

    def test_refresh_output_rejects_unknown_module(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Refresh Unknown",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/modules/{project_id}/fake_module_xyz/refresh-output",
        )
        assert resp.status_code == 404

    def test_refresh_output_rejects_nonexistent_project(self, client):
        """Should return 404 for a project that doesn't exist."""
        import uuid as _uuid
        fake_pid = str(_uuid.uuid4())

        resp = client.post(
            f"/api/v1/modules/{fake_pid}/brand_identity_framework/refresh-output",
        )
        assert resp.status_code == 404


class TestAddPathwayModules:
    """Tests for POST /projects/{project_id}/pathway/modules."""

    def test_add_modules_appends_and_deduplicates(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Add Modules Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Get current modules from pathway
        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        assert pathway_resp.status_code == 200
        original_modules = pathway_resp.json()["modules"]

        # Pick a module NOT already in the pathway to add
        all_mods_resp = client.get("/api/v1/meta/modules")
        all_ids = [m["id"] for m in all_mods_resp.json()]
        existing_set = set(original_modules)
        to_add = [mid for mid in all_ids if mid not in existing_set][:2]
        assert len(to_add) > 0, "Should have modules available to add"

        # Add the new modules
        resp = client.post(
            f"/api/v1/projects/{project_id}/pathway/modules",
            json={"module_ids": to_add},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert set(body["added"]) == set(to_add)
        assert all(mid in body["modules"] for mid in to_add)
        # Original modules still present
        assert all(mid in body["modules"] for mid in original_modules)

        # Adding same modules again should be a no-op (deduplication)
        resp2 = client.post(
            f"/api/v1/projects/{project_id}/pathway/modules",
            json={"module_ids": to_add},
        )
        assert resp2.status_code == 200
        assert resp2.json()["added"] == []

    def test_add_modules_rejects_unknown_ids(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Add Unknown Modules",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/projects/{project_id}/pathway/modules",
            json={"module_ids": ["totally_fake_module_xyz"]},
        )
        assert resp.status_code == 422
        assert "Unknown module IDs" in resp.json()["detail"]

    def test_add_modules_rejects_empty_list(self, client):
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Add Empty Modules",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        resp = client.post(
            f"/api/v1/projects/{project_id}/pathway/modules",
            json={"module_ids": []},
        )
        assert resp.status_code == 400


# ── 7. Scoped sessions (Phase 6) ────────────────────────────────────────


class TestScopedSessions:
    """Tests for mini-Discovery scoped session support (Phase 6)."""

    def test_start_scoped_session_creates_new(self, client):
        """Starting with scope_module_ids always creates a new session."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Scoped Session Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Get a valid module ID from the assembled pathway
        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        valid_module = pathway_resp.json()["modules"][0]

        # Start a main-flow session first
        main_resp = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id},
        )
        assert main_resp.status_code == 201
        main_session_id = main_resp.json()["id"]

        # Start a scoped session for specific modules
        scoped_resp = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": [valid_module],
            },
        )
        assert scoped_resp.status_code == 201
        scoped_body = scoped_resp.json()
        assert scoped_body["id"] != main_session_id
        assert scoped_body["scope_module_ids"] == [valid_module]

    def test_scoped_session_does_not_hijack_main_resume(self, client):
        """Resuming without scope_module_ids should not return a scoped session."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Scope Isolation Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Get a valid module ID from the assembled pathway
        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        valid_module = pathway_resp.json()["modules"][0]

        # Create main-flow session
        main_resp = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id},
        )
        main_session_id = main_resp.json()["id"]

        # Create a scoped session
        client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": [valid_module],
            },
        )

        # Resume without scope — should get main session back
        resume_resp = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id},
        )
        assert resume_resp.status_code == 201
        assert resume_resp.json()["id"] == main_session_id

    def test_scoped_session_always_creates_new_even_with_existing_scope(self, client):
        """Each scoped start creates a fresh session, never resumes a prior scoped one."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Scope No Resume",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Get a valid module ID from the assembled pathway
        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        valid_module = pathway_resp.json()["modules"][0]

        # Create two scoped sessions for the same modules
        s1 = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": [valid_module],
            },
        )
        s2 = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": [valid_module],
            },
        )
        assert s1.json()["id"] != s2.json()["id"]

    def test_field_summary_respects_scope(self, client):
        """GET /discovery/{session_id}/field-summary scopes to session modules."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Scope Summary Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Get full pathway to compare
        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        all_modules = pathway_resp.json()["modules"]
        assert len(all_modules) > 1, "Need multiple modules to test scope filtering"

        # Start main-flow session and get its field summary
        main_resp = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id},
        )
        main_sid = main_resp.json()["id"]
        main_summary = client.get(f"/api/v1/discovery/{main_sid}/field-summary")
        assert main_summary.status_code == 200
        main_module_count = len(main_summary.json()["per_module"])

        # Start scoped session with just 1 module
        scoped_resp = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": [all_modules[0]],
            },
        )
        scoped_sid = scoped_resp.json()["id"]
        scoped_summary = client.get(f"/api/v1/discovery/{scoped_sid}/field-summary")
        assert scoped_summary.status_code == 200
        scoped_module_count = len(scoped_summary.json()["per_module"])

        assert scoped_module_count == 1
        assert scoped_module_count < main_module_count

    def test_empty_scope_module_ids_behaves_as_unscoped(self, client):
        """An empty scope_module_ids list is normalized to None (unscoped resume)."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Empty Scope Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Start a session
        s1 = client.post("/api/v1/discovery/start", json={"project_id": project_id})
        sid1 = s1.json()["id"]

        # Start with empty scope — should resume the existing session
        s2 = client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id, "scope_module_ids": []},
        )
        assert s2.status_code == 201
        assert s2.json()["id"] == sid1
        assert s2.json()["scope_module_ids"] is None

    def test_scoped_session_with_nonexistent_module_ids(self, client):
        """Scoped session with invalid module IDs returns 400."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Invalid Scope Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        scoped_resp = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": ["totally_fake_module_xyz"],
            },
        )
        assert scoped_resp.status_code == 400
        assert "Invalid module IDs" in scoped_resp.json()["detail"]

    def test_scoped_session_on_v1_project_rejected(self, client):
        """Scoped sessions are rejected for v1 projects."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "V1 Scope Test",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        scoped_resp = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": ["some_module"],
            },
        )
        assert scoped_resp.status_code == 400
        assert "v2" in scoped_resp.json()["detail"]

    def test_scoped_session_with_multiple_module_ids(self, client):
        """Scoped sessions work with multiple valid module IDs."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Multi Scope Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        all_modules = pathway_resp.json()["modules"]
        assert len(all_modules) >= 2

        scope = all_modules[:2]
        scoped_resp = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": scope,
            },
        )
        assert scoped_resp.status_code == 201
        assert set(scoped_resp.json()["scope_module_ids"]) == set(scope)

        # Field summary should show exactly 2 modules
        scoped_sid = scoped_resp.json()["id"]
        summary = client.get(f"/api/v1/discovery/{scoped_sid}/field-summary")
        assert summary.status_code == 200
        assert len(summary.json()["per_module"]) == 2


# ── 8. Regression tests for audit fixes ────────────────────────────────


class TestAuditFixRegressions:
    """Regression tests confirming audit fixes don't break existing behavior."""

    def test_library_excludes_scoped_sessions_from_progress(self, client):
        """Library endpoint should reflect main-flow session status, not scoped sessions."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Library Regression",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Create a main-flow session
        client.post("/api/v1/discovery/start", json={"project_id": project_id})

        # Create a scoped session
        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        valid_module = pathway_resp.json()["modules"][0]
        client.post(
            "/api/v1/discovery/start",
            json={"project_id": project_id, "scope_module_ids": [valid_module]},
        )

        # Library should still show the project — scope filter shouldn't hide it
        lib_resp = client.get("/api/v1/library/projects")
        assert lib_resp.status_code == 200
        project_ids = [p["id"] for p in lib_resp.json()]
        assert project_id in project_ids

    def test_main_flow_start_still_resumes_after_scoped_sessions(self, client):
        """Creating scoped sessions must not break normal session resume."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Resume Regression",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Start main session
        s1 = client.post("/api/v1/discovery/start", json={"project_id": project_id})
        main_id = s1.json()["id"]

        # Create several scoped sessions
        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        modules = pathway_resp.json()["modules"]
        for mod_id in modules[:3]:
            client.post(
                "/api/v1/discovery/start",
                json={"project_id": project_id, "scope_module_ids": [mod_id]},
            )

        # Resume should still return the original main session
        s2 = client.post("/api/v1/discovery/start", json={"project_id": project_id})
        assert s2.json()["id"] == main_id

    def test_v1_project_discovery_unaffected_by_scope_validation(self, client):
        """v1 projects (no primary_category) still work with normal discovery start."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "V1 Regression",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        # Normal start should work fine for v1
        s1 = client.post("/api/v1/discovery/start", json={"project_id": project_id})
        assert s1.status_code == 201
        assert s1.json()["scope_module_ids"] is None

        # Resume should also work
        s2 = client.post("/api/v1/discovery/start", json={"project_id": project_id})
        assert s2.status_code == 201
        assert s2.json()["id"] == s1.json()["id"]

    def test_mixed_valid_invalid_scope_ids_rejected(self, client):
        """If any scope_module_id is invalid, the whole request is rejected."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Mixed IDs Test",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        valid_module = pathway_resp.json()["modules"][0]

        # Mix valid + invalid
        scoped_resp = client.post(
            "/api/v1/discovery/start",
            json={
                "project_id": project_id,
                "scope_module_ids": [valid_module, "totally_bogus_xyz"],
            },
        )
        assert scoped_resp.status_code == 400
        assert "totally_bogus_xyz" in scoped_resp.json()["detail"]

    def test_scope_null_in_response_for_normal_sessions(self, client):
        """Normal (unscoped) sessions always return scope_module_ids=null."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Null Scope Check",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        s = client.post("/api/v1/discovery/start", json={"project_id": project_id})
        assert s.status_code == 201
        assert s.json()["scope_module_ids"] is None

    def test_field_summary_for_main_session_shows_all_modules(self, client):
        """Main-flow field summary returns all pathway modules, not a filtered subset."""
        resp = client.post(
            "/api/v1/projects",
            json={
                "name": "Summary Regression",
                "primary_category": "software_tech",
                "ai_partner_style": "strategist",
            },
        )
        project_id = resp.json()["id"]

        pathway_resp = client.get(f"/api/v1/projects/{project_id}/pathway")
        total_modules = len(pathway_resp.json()["modules"])

        s = client.post("/api/v1/discovery/start", json={"project_id": project_id})
        summary = client.get(f"/api/v1/discovery/{s.json()['id']}/field-summary")
        assert summary.status_code == 200
        assert len(summary.json()["per_module"]) == total_modules
