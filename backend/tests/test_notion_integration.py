"""
Tests for the Notion integration — pure rendering/OAuth-state logic plus the
HTTP routes (authorize / callback / pages / push).

Mock boundary: only the network/config edges are faked —
``notion_service.is_configured`` (so tests don't depend on real env vars),
``exchange_code_for_token``, ``list_accessible_pages``, and
``create_design_kit_page`` (the httpx calls). The state-token signing, the
block renderer, the route wiring, ownership checks, and the encrypted-token
round-trip all run for real.

Notes:
  - ``render_design_kit_blocks`` is a pure function — tested directly, no app.
  - The OAuth ``state`` is a real HS256 JWT; the secret falls back to
    CLERK_SECRET_KEY, which the test sets via env in the ``signing_secret``
    fixture (conftest only sets DATABASE_URL + ANTHROPIC_KEY).
  - Token encryption needs INTEGRATION_TOKEN_KEY; the ``token_key`` fixture
    sets a real Fernet key so the callback's encrypt path runs end to end.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.encryption import encrypt_secret
from app.main import app
from app.models.external_integration import ExternalIntegration
from app.models.project import Project
from app.models.user import User
from app.routers import integrations as ig
from app.routers.auth import get_current_user
from app.services import notion_service


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User):
    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def signing_secret(monkeypatch):
    """Ensure an HS256 signing secret exists for the OAuth state token."""
    monkeypatch.setattr(settings, "SHARE_ACCESS_SECRET", "test-share-secret-please", raising=False)
    return "test-share-secret-please"


@pytest.fixture
def token_key(monkeypatch):
    """Provide a valid Fernet key so encrypt/decrypt of the stored token works."""
    key = Fernet.generate_key().decode("utf-8")
    monkeypatch.setattr(settings, "INTEGRATION_TOKEN_KEY", key, raising=False)
    return key


@pytest.fixture
def configured(monkeypatch):
    """Pretend the server has Notion OAuth env vars set."""
    monkeypatch.setattr(settings, "NOTION_CLIENT_ID", "client-abc", raising=False)
    monkeypatch.setattr(settings, "NOTION_CLIENT_SECRET", "secret-xyz", raising=False)
    monkeypatch.setattr(
        settings, "NOTION_REDIRECT_URI",
        "https://backend.example.com/api/v1/integrations/notion/callback",
        raising=False,
    )


# ── 1. Pure: configuration + authorize URL ───────────────────────────────────


class TestConfig:
    def test_not_configured_by_default(self, monkeypatch):
        monkeypatch.setattr(settings, "NOTION_CLIENT_ID", "", raising=False)
        monkeypatch.setattr(settings, "NOTION_CLIENT_SECRET", "", raising=False)
        monkeypatch.setattr(settings, "NOTION_REDIRECT_URI", "", raising=False)
        assert notion_service.is_configured() is False

    def test_configured_when_all_set(self, configured):
        assert notion_service.is_configured() is True

    def test_partial_config_is_not_configured(self, monkeypatch):
        monkeypatch.setattr(settings, "NOTION_CLIENT_ID", "x", raising=False)
        monkeypatch.setattr(settings, "NOTION_CLIENT_SECRET", "", raising=False)
        monkeypatch.setattr(settings, "NOTION_REDIRECT_URI", "y", raising=False)
        assert notion_service.is_configured() is False

    def test_authorize_url_contains_state_and_client(self, configured):
        url = notion_service.build_authorize_url("STATE-TOKEN-123")
        assert url.startswith(notion_service.NOTION_AUTHORIZE_URL)
        assert "state=STATE-TOKEN-123" in url
        assert "client_id=client-abc" in url
        assert "response_type=code" in url
        # redirect_uri must be URL-encoded
        assert "redirect_uri=https%3A%2F%2Fbackend.example.com" in url


# ── 2. Pure: block rendering ─────────────────────────────────────────────────


class TestRenderBlocks:
    def test_v1_renders_header_and_sheet(self):
        ctx = {
            "project_name": "MealMate",
            "project_description": "Plan weekly meals",
            "flow_version": "v1",
            "platform": "web",
            "problem": "Cooks waste food",
            "mvp": "Weekly planner",
            "features": ["Grocery list", "Recipe import"],
        }
        blocks = notion_service.render_design_kit_blocks(ctx)
        # First block is an H1 with the project name.
        assert blocks[0]["type"] == "heading_1"
        assert blocks[0]["heading_1"]["rich_text"][0]["text"]["content"] == "MealMate"
        flat = _flatten_text(blocks)
        assert "Cooks waste food" in flat
        assert "Weekly planner" in flat
        assert "Grocery list" in flat
        assert "myide.ai" in flat  # footer

    def test_v2_renders_modules_with_filled_fields(self):
        ctx = {
            "project_name": "Acme",
            "flow_version": "v2",
            "platform": "web",
            "modules": [
                {
                    "module_id": "audience_persona_builder",
                    "label": "Audience Persona",
                    "fields": [
                        {"key": "primary_persona", "label": "Primary Persona"},
                        {"key": "pain_points", "label": "Pain Points"},
                        {"key": "empty_field", "label": "Empty"},
                    ],
                    "responses": {
                        "primary_persona": "Early-stage founders",
                        "pain_points": ["Time", "Money"],
                        "empty_field": "",
                        "__generated_output": {"title": "x", "content": "y"},
                    },
                },
                {
                    "module_id": "no_responses_module",
                    "label": "Nothing Here",
                    "fields": [{"key": "a", "label": "A"}],
                    "responses": {},
                },
            ],
        }
        blocks = notion_service.render_design_kit_blocks(ctx)
        flat = _flatten_text(blocks)
        assert "Audience Persona" in flat
        assert "Early-stage founders" in flat
        assert "Time, Money" in flat  # list joined
        # Internal + empty fields excluded.
        assert "__generated_output" not in flat
        # A module with no responses is skipped entirely.
        assert "Nothing Here" not in flat

    def test_v2_falls_back_to_discovery_summary(self):
        ctx = {
            "project_name": "Acme",
            "flow_version": "v2",
            "modules": [],
            "discovery_summary": "## Brief\n- key: value",
        }
        blocks = notion_service.render_design_kit_blocks(ctx)
        flat = _flatten_text(blocks)
        assert "Discovery Summary" in flat
        assert "key: value" in flat

    def test_renders_blocks_and_pipeline_from_orm_like(self):
        class _B:
            def __init__(self, name, priority, effort):
                self.name, self.priority, self.effort = name, priority, effort

        class _P:
            def __init__(self, layer, tool):
                self.layer, self.selected_tool = layer, tool

        ctx = {
            "project_name": "Acme",
            "flow_version": "v1",
            "problem": "p",
            "blocks": [_B("Login", "mvp", "M"), _B("Dashboard", "v2", "L")],
            "pipeline": [_P("Frontend", "React"), _P("Backend", "FastAPI")],
        }
        blocks = notion_service.render_design_kit_blocks(ctx)
        flat = _flatten_text(blocks)
        assert "Feature Blocks" in flat
        assert "Login" in flat and "Dashboard" in flat
        assert "Tech Stack" in flat
        assert "Frontend: React" in flat and "Backend: FastAPI" in flat

    def test_long_text_is_truncated_to_notion_limit(self):
        ctx = {
            "project_name": "Acme",
            "flow_version": "v1",
            "problem": "x" * 5000,
        }
        blocks = notion_service.render_design_kit_blocks(ctx)
        for b in blocks:
            for rt in b.get(b["type"], {}).get("rich_text", []):
                assert len(rt["text"]["content"]) <= notion_service._MAX_RICH_TEXT

    def test_value_text_handles_types(self):
        assert notion_service._value_text(None) == ""
        assert notion_service._value_text("  hi  ") == "hi"
        assert notion_service._value_text(True) == "Yes"
        assert notion_service._value_text(["a", "", "b"]) == "a, b"
        assert notion_service._value_text({"k": "v", "empty": ""}) == "k: v"


def _flatten_text(blocks: list[dict]) -> str:
    """Concatenate all rich_text content from a block list for assertions."""
    out = []
    for b in blocks:
        body = b.get(b.get("type", ""), {})
        for rt in body.get("rich_text", []):
            out.append(rt.get("text", {}).get("content", ""))
    return "\n".join(out)


# ── 3. OAuth state token round-trip ──────────────────────────────────────────


class TestOAuthState:
    def test_mint_and_verify_roundtrip(self, signing_secret):
        uid = uuid.uuid4()
        token = ig._mint_oauth_state(uid)
        assert ig._verify_oauth_state(token) == uid

    def test_verify_rejects_tampered_token(self, signing_secret):
        token = ig._mint_oauth_state(uuid.uuid4())
        with pytest.raises(ValueError):
            ig._verify_oauth_state(token + "tamper")

    def test_verify_rejects_wrong_scope(self, signing_secret, monkeypatch):
        import jwt
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        bad = jwt.encode(
            {"sub": str(uuid.uuid4()), "scope": "something_else",
             "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=5)).timestamp())},
            signing_secret, algorithm="HS256",
        )
        with pytest.raises(ValueError):
            ig._verify_oauth_state(bad)


# ── 4. Routes: authorize ─────────────────────────────────────────────────────


class TestAuthorizeRoute:
    def test_authorize_503_when_unconfigured(self, client, monkeypatch):
        monkeypatch.setattr(notion_service, "is_configured", lambda: False)
        resp = client.post("/api/v1/integrations/notion/authorize")
        assert resp.status_code == 503

    def test_authorize_returns_url_when_configured(
        self, client, configured, signing_secret
    ):
        resp = client.post("/api/v1/integrations/notion/authorize")
        assert resp.status_code == 200, resp.text
        url = resp.json()["authorize_url"]
        assert url.startswith(notion_service.NOTION_AUTHORIZE_URL)
        assert "state=" in url


# ── 5. Routes: callback ──────────────────────────────────────────────────────


class TestCallbackRoute:
    def test_callback_error_param_redirects_to_settings_error(self, client):
        resp = client.get(
            "/api/v1/integrations/notion/callback?error=access_denied",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "notion=error" in resp.headers["location"]

    def test_callback_bad_state_redirects_error(self, client, configured, signing_secret):
        resp = client.get(
            "/api/v1/integrations/notion/callback?code=abc&state=not-a-jwt",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "notion=error" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_callback_success_stores_encrypted_token(
        self, client, db_session, test_user, configured, signing_secret, token_key, monkeypatch
    ):
        async def fake_exchange(code):
            assert code == "good-code"
            return {
                "access_token": "secret_notion_token_value",
                "workspace_id": "ws-1",
                "workspace_name": "My Workspace",
                "bot_id": "bot-1",
            }

        monkeypatch.setattr(notion_service, "exchange_code_for_token", fake_exchange)

        state = ig._mint_oauth_state(test_user.id)
        resp = client.get(
            f"/api/v1/integrations/notion/callback?code=good-code&state={state}",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "notion=connected" in resp.headers["location"]

        # A row was created, the token is encrypted (not plaintext), workspace saved.
        row = (
            await db_session.execute(
                select(ExternalIntegration).where(
                    ExternalIntegration.user_id == test_user.id,
                    ExternalIntegration.provider == "notion",
                )
            )
        ).scalar_one()
        assert row.access_token and row.access_token != "secret_notion_token_value"
        assert row.config["workspace_name"] == "My Workspace"
        from app.core.encryption import decrypt_secret
        assert decrypt_secret(row.access_token) == "secret_notion_token_value"

    @pytest.mark.asyncio
    async def test_callback_token_exchange_failure_redirects_error(
        self, client, test_user, configured, signing_secret, token_key, monkeypatch
    ):
        async def boom(code):
            raise RuntimeError("notion said no")

        monkeypatch.setattr(notion_service, "exchange_code_for_token", boom)
        state = ig._mint_oauth_state(test_user.id)
        resp = client.get(
            f"/api/v1/integrations/notion/callback?code=x&state={state}",
            follow_redirects=False,
        )
        assert resp.status_code in (302, 307)
        assert "notion=error" in resp.headers["location"]


# ── 6. Routes: push ──────────────────────────────────────────────────────────


class TestPushRoute:
    def test_push_404_when_not_connected(self, client):
        resp = client.post(
            f"/api/v1/integrations/notion/push/{uuid.uuid4()}",
            json={"parent_page_id": "page-1"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_push_creates_page_for_owned_project(
        self, client, db_session, test_user, token_key, monkeypatch
    ):
        # Connect Notion (store an encrypted token directly).
        db_session.add(
            ExternalIntegration(
                user_id=test_user.id,
                provider="notion",
                access_token=encrypt_secret("tok"),
                config={},
                enabled=True,
            )
        )
        # Owned v1 project.
        project = Project(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Pushable",
            description="desc",
            flow_version="v1",
        )
        db_session.add(project)
        await db_session.commit()

        captured = {}

        async def fake_create(token, parent_page_id, title, blocks):
            captured["token"] = token
            captured["parent"] = parent_page_id
            captured["title"] = title
            captured["n_blocks"] = len(blocks)
            return {"id": "new-page-id", "url": "https://notion.so/new-page-id"}

        monkeypatch.setattr(notion_service, "create_design_kit_page", fake_create)

        resp = client.post(
            f"/api/v1/integrations/notion/push/{project.id}",
            json={"parent_page_id": "parent-123"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "pushed"
        assert body["url"] == "https://notion.so/new-page-id"
        assert captured["token"] == "tok"  # decrypted before the call
        assert captured["parent"] == "parent-123"
        assert captured["title"] == "Pushable"
        assert captured["n_blocks"] > 0

    @pytest.mark.asyncio
    async def test_push_404_for_other_users_project(
        self, client, db_session, test_user, token_key, monkeypatch
    ):
        db_session.add(
            ExternalIntegration(
                user_id=test_user.id, provider="notion",
                access_token=encrypt_secret("tok"), config={}, enabled=True,
            )
        )
        other = User(
            id=uuid.uuid4(), email=f"other-{uuid.uuid4().hex[:6]}@e.com",
            name="O", display_name="O", email_verified=True, account_type="free",
        )
        db_session.add(other)
        await db_session.flush()
        foreign = Project(
            id=uuid.uuid4(), user_id=other.id, name="NotYours", flow_version="v1",
        )
        db_session.add(foreign)
        await db_session.commit()

        # Should not even reach Notion — ownership check fails first.
        monkeypatch.setattr(
            notion_service, "create_design_kit_page",
            lambda *a, **k: pytest.fail("should not create page for unowned project"),
        )
        resp = client.post(
            f"/api/v1/integrations/notion/push/{foreign.id}",
            json={"parent_page_id": "p"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_push_400_when_no_parent_page(
        self, client, db_session, test_user, token_key
    ):
        db_session.add(
            ExternalIntegration(
                user_id=test_user.id, provider="notion",
                access_token=encrypt_secret("tok"), config={}, enabled=True,
            )
        )
        project = Project(id=uuid.uuid4(), user_id=test_user.id, name="P", flow_version="v1")
        db_session.add(project)
        await db_session.commit()

        resp = client.post(
            f"/api/v1/integrations/notion/push/{project.id}",
            json={},  # no parent_page_id, none stored in config
        )
        assert resp.status_code == 400


# ── 7. list_integrations advertises notion as available ──────────────────────


class TestListIntegrations:
    def test_notion_listed_available_not_coming_soon(self, client):
        resp = client.get("/api/v1/integrations")
        assert resp.status_code == 200
        by_provider = {i["provider"]: i for i in resp.json()}
        assert by_provider["notion"]["status"] == "available"
        # A still-stubbed provider stays coming_soon.
        assert by_provider["trello"]["status"] == "coming_soon"
