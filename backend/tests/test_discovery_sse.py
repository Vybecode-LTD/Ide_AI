"""
SSE streaming tests for the Discovery endpoints — POST /discovery/{id}/init and
POST /discovery/{id}/message.

These close the last big v2 backend coverage gap noted in CONTEXT_HANDOFF.md.
The service-layer tests in ``test_discovery_v2.py`` and the HTTP tests in
``test_discovery_v2_integration.py`` deliberately avoided the streaming routes
because they require mocking the Anthropic streaming client. This file does
exactly that — and ONLY that.

Mock boundary (the only things faked):
  - ``ai_service.stream_response``      → yields a canned token sequence
  - ``ai_service.generate_quick_chips`` → returns canned chips
  - ``ai_service.extract_module_fields``→ returns a canned v2 extraction dict
  - ``discovery_service.extract_sheet_fields`` → canned v1 extraction dict
    (patched where it is *used* — discovery_service imports the name directly)

Everything else runs for real: flow_version branching, prompt construction
(the prompt builders never call the network), message persistence, the
design-sheet update, field-summary aggregation, and the SSE event assembly
itself. So these are true integration tests of the streaming routes.

What they prove:
  - init streams tokens, persists the greeting, and ALWAYS emits ``done`` + chips
  - message streams tokens then emits the extraction event BEFORE ``done``
  - v2 projects emit ``field_update`` (+ a summary); v1 projects emit
    ``sheet_update`` — the two flows are driven by ``project.flow_version``
  - the v2 unified prompt and the v1 stage prompt are genuinely different
    (prompt-branching, captured off the stream mock)
  - extraction that raises mid-stream still yields a ``done`` sentinel
    (the try/except hardening in discovery.py)

Known harness limit:
  Writing *newly extracted* field values exercises the PostgreSQL
  ``INSERT ... ON CONFLICT ... responses || EXCLUDED.responses`` upsert, whose
  ``||`` is JSONB-merge in Postgres but string-concat in SQLite — so that one
  path is PG-only and lives behind a documented skip below. Summary aggregation
  is instead proven by seeding a value through the real PATCH endpoint (which is
  SQLite-safe) and asserting the SSE summary reflects it.
"""
from __future__ import annotations

import json
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import app
from app.routers.auth import get_current_user
from app.services import ai_service, discovery_service
from app.models.user import User


# ── SSE parsing helpers ─────────────────────────────────────────────────────


def parse_sse(body: str) -> list[dict]:
    """Parse a ``text/event-stream`` body into a list of decoded JSON events.

    Each event in these routes is emitted as a single ``data: {json}\\n\\n``
    frame. A ``data:`` frame we can't decode is a real failure for these routes.
    """
    events: list[dict] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[len("data:"):].strip()
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            raise AssertionError(f"Un-decodable SSE data frame: {payload!r}")
    return events


def event_types(events: list[dict]) -> list[str]:
    return [e.get("type") for e in events]


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, test_user: User):
    """FastAPI TestClient with db + auth dependency overrides.

    Mirrors the fixture in test_discovery_v2_integration.py so this file is
    self-contained.
    """
    async def override_get_db():
        yield db_session

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def ai(monkeypatch):
    """Mock the AI boundary the streaming routes depend on.

    Returns a mutable ``state`` dict so each test can tune the canned tokens,
    chips, and extraction results, and can read back the system prompts the
    stream was actually invoked with (to assert flow-version prompt branching).
    """
    state: dict = {
        "tokens": ["Hello", " there", "!"],
        "chips": ["Option A", "Option B", "Option C"],
        "module_extract": {},    # returned by extract_module_fields (v2)
        "sheet_extract": {},      # returned by extract_sheet_fields (v1)
        "modules_raise": False,   # make extract_module_fields blow up
        "captured": {"system_prompts": [], "stream_messages": []},
    }

    def fake_stream(messages, system_prompt):
        # Capture synchronously at call time, before iteration begins.
        state["captured"]["system_prompts"].append(system_prompt)
        state["captured"]["stream_messages"].append(messages)

        async def _gen():
            for tok in state["tokens"]:
                yield tok

        return _gen()

    async def fake_chips(ai_response, stage="greeting"):
        return list(state["chips"])

    async def fake_extract_modules(messages, modules, current_fields):
        if state["modules_raise"]:
            raise RuntimeError("simulated extraction failure")
        return dict(state["module_extract"])

    async def fake_extract_sheet(messages, *, pathway=None):
        return dict(state["sheet_extract"])

    monkeypatch.setattr(ai_service, "stream_response", fake_stream)
    monkeypatch.setattr(ai_service, "generate_quick_chips", fake_chips)
    monkeypatch.setattr(ai_service, "extract_module_fields", fake_extract_modules)
    # discovery_service imports extract_sheet_fields by name → patch it there.
    monkeypatch.setattr(discovery_service, "extract_sheet_fields", fake_extract_sheet)

    return state


# ── Project/session helpers ─────────────────────────────────────────────────


def _make_v2_project(client, name="SSE v2") -> str:
    resp = client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "description": "A v2 project for SSE tests",
            "primary_category": "software_tech",
            "ai_partner_style": "strategist",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["flow_version"] == "v2", resp.text
    return resp.json()["id"]


def _make_v1_project(client, name="SSE v1") -> str:
    # No primary_category → H1 downgrade → flow_version v1.
    resp = client.post(
        "/api/v1/projects",
        json={
            "name": name,
            "description": "A v1 project for SSE tests",
            "ai_partner_style": "strategist",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["flow_version"] == "v1", resp.text
    return resp.json()["id"]


def _start_session(client, project_id: str) -> str:
    resp = client.post("/api/v1/discovery/start", json={"project_id": project_id})
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _first_text_field(client, project_id: str) -> tuple[str, str]:
    """Return (module_id, field_key) of the first text/longtext field in the
    assembled pathway — a SQLite-safe target for the PATCH endpoint."""
    kit = client.get(f"/api/v1/projects/{project_id}/design-kit").json()
    for mod in kit["modules"]:
        for f in mod["fields"]:
            if f["type"] in ("text", "longtext"):
                return mod["module_id"], f["key"]
    raise AssertionError("expected at least one text/longtext field in the pathway")


# ── 1. init greeting (v2) ───────────────────────────────────────────────────


class TestInitGreetingV2:
    def test_streams_tokens_and_persists_greeting(self, client, ai):
        ai["tokens"] = ["Welcome", " to", " discovery"]
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)

        resp = client.post(f"/api/v1/discovery/{sid}/init")
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/event-stream")

        events = parse_sse(resp.text)
        types = event_types(events)

        token_text = "".join(e["content"] for e in events if e["type"] == "token")
        assert token_text == "Welcome to discovery"
        assert types[-1] == "done"
        assert types.count("done") == 1

        # init does NOT emit extraction events.
        assert "field_update" not in types
        assert "sheet_update" not in types

        # The greeting was persisted — read the session back through the API.
        sess = client.get(f"/api/v1/discovery/{sid}").json()
        assert len(sess["messages"]) == 1
        assert sess["messages"][0]["role"] == "assistant"
        assert sess["messages"][0]["content"] == "Welcome to discovery"

    def test_done_event_always_carries_chips(self, client, ai):
        ai["chips"] = ["Build an MVP", "Validate first", "Talk to users"]
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)

        resp = client.post(f"/api/v1/discovery/{sid}/init")
        done = parse_sse(resp.text)[-1]
        assert done["type"] == "done"
        assert done["chips"] == ["Build an MVP", "Validate first", "Talk to users"]

    def test_uses_unified_greeting_prompt(self, client, ai):
        """v2 init builds the unified greeting prompt (references the project)."""
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)

        client.post(f"/api/v1/discovery/{sid}/init")
        assert ai["captured"]["system_prompts"], "stream_response was never called"
        prompt = ai["captured"]["system_prompts"][-1]
        # The unified greeting names the project and the assembled module set.
        assert "SSE v2" in prompt
        assert "MODULES IN THIS DESIGN KIT" in prompt


# ── 2. init greeting (v1) ───────────────────────────────────────────────────


class TestInitGreetingV1:
    def test_streams_tokens_and_emits_done(self, client, ai):
        ai["tokens"] = ["Hi", " let's", " start"]
        pid = _make_v1_project(client)
        sid = _start_session(client, pid)

        resp = client.post(f"/api/v1/discovery/{sid}/init")
        assert resp.status_code == 200, resp.text
        events = parse_sse(resp.text)
        types = event_types(events)

        assert "".join(e["content"] for e in events if e["type"] == "token") == "Hi let's start"
        assert types[-1] == "done"
        assert "field_update" not in types
        assert "sheet_update" not in types

    def test_v1_greeting_prompt_differs_from_v2(self, client, ai):
        """The v1 legacy greeting prompt is not the v2 unified one."""
        v1_pid = _make_v1_project(client, name="LegacyProj")
        v1_sid = _start_session(client, v1_pid)
        client.post(f"/api/v1/discovery/{v1_sid}/init")
        v1_prompt = ai["captured"]["system_prompts"][-1]
        assert "MODULES IN THIS DESIGN KIT" not in v1_prompt

        v2_pid = _make_v2_project(client, name="UnifiedProj")
        v2_sid = _start_session(client, v2_pid)
        client.post(f"/api/v1/discovery/{v2_sid}/init")
        v2_prompt = ai["captured"]["system_prompts"][-1]

        assert v1_prompt != v2_prompt


# ── 3. init edge cases ──────────────────────────────────────────────────────


class TestInitEdgeCases:
    def test_init_missing_session_404(self, client, ai):
        resp = client.post(f"/api/v1/discovery/{uuid.uuid4()}/init")
        assert resp.status_code == 404

    def test_init_rejects_already_initialized_session(self, client, ai):
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)

        first = client.post(f"/api/v1/discovery/{sid}/init")
        assert first.status_code == 200
        # Greeting now persisted → a second init must be rejected.
        second = client.post(f"/api/v1/discovery/{sid}/init")
        assert second.status_code == 400
        assert "initialized" in second.json()["detail"].lower()


# ── 4. send message (v2) ────────────────────────────────────────────────────


class TestSendMessageV2:
    def test_emits_field_update_before_done(self, client, ai):
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)

        resp = client.post(
            f"/api/v1/discovery/{sid}/message",
            json={"content": "It helps home cooks plan weekly meals."},
        )
        assert resp.status_code == 200, resp.text
        events = parse_sse(resp.text)
        types = event_types(events)

        assert "token" in types
        assert "field_update" in types
        assert "sheet_update" not in types, "v2 must not emit the v1 sheet event"
        assert types[-1] == "done"

        # Ordering contract: extraction event precedes the done sentinel.
        assert types.index("field_update") < types.index("done")

        fu = next(e for e in events if e["type"] == "field_update")
        assert "summary" in fu and "updates" in fu
        for key in ("total_filled", "total_fields", "required_total", "overall_percent", "per_module"):
            assert key in fu["summary"], f"missing {key} in field_update summary"

    def test_field_update_summary_reflects_persisted_responses(self, client, ai):
        """A value persisted via PATCH shows up in the live SSE summary.

        This proves the SSE field-summary aggregation reads real
        ``module_responses`` rows — without depending on the PG-only extraction
        upsert (see the skipped test below). Extraction is left empty so no
        upsert is attempted; the PATCH seed is the source of the filled field.
        """
        pid = _make_v2_project(client)
        mid, fkey = _first_text_field(client, pid)

        # Seed one field via the SQLite-safe PATCH endpoint.
        patch = client.patch(
            f"/api/v1/modules/{pid}/{mid}/responses",
            json={fkey: "A concrete persisted answer"},
        )
        assert patch.status_code == 200, patch.text

        sid = _start_session(client, pid)
        resp = client.post(
            f"/api/v1/discovery/{sid}/message",
            json={"content": "Anything — extraction is mocked empty."},
        )
        assert resp.status_code == 200, resp.text
        events = parse_sse(resp.text)
        fu = next(e for e in events if e["type"] == "field_update")

        # The persisted value is reflected in the aggregate + the per-module row.
        assert fu["summary"]["total_filled"] >= 1
        target_row = next(m for m in fu["summary"]["per_module"] if m["module_id"] == mid)
        assert target_row["filled"] >= 1

        # Both turns of THIS message exchange are persisted, in order.
        sess = client.get(f"/api/v1/discovery/{sid}").json()
        assert [m["role"] for m in sess["messages"]] == ["user", "assistant"]

    @pytest.mark.skip(
        reason="PG-only path: apply_extracted_module_fields upserts via "
        "INSERT ... ON CONFLICT ... responses || EXCLUDED.responses, whose '||' "
        "is JSONB-merge in Postgres but string-concat in SQLite. Un-skip when a "
        "PostgreSQL-backed test harness (e.g. testcontainers) is added. "
        "Owner: backend. Tracked in CONTEXT_HANDOFF.md 'Known gaps'."
    )
    def test_extraction_upsert_writes_new_field(self, client, ai):
        pid = _make_v2_project(client)
        mid, fkey = _first_text_field(client, pid)
        ai["module_extract"] = {f"{mid}.{fkey}": "A newly extracted answer"}

        sid = _start_session(client, pid)
        resp = client.post(
            f"/api/v1/discovery/{sid}/message",
            json={"content": "Here is my detailed answer."},
        )
        events = parse_sse(resp.text)
        fu = next(e for e in events if e["type"] == "field_update")
        assert fu["summary"]["total_filled"] >= 1
        assert any(u["field_key"] == fkey for u in fu["updates"])

    def test_extraction_failure_still_emits_done(self, client, ai):
        """If extract_module_fields raises, the stream still completes cleanly."""
        ai["modules_raise"] = True
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)

        resp = client.post(
            f"/api/v1/discovery/{sid}/message",
            json={"content": "trigger extraction"},
        )
        assert resp.status_code == 200, resp.text
        events = parse_sse(resp.text)
        types = event_types(events)

        assert "token" in types
        # Extraction blew up → no field_update — but done must still fire.
        assert "field_update" not in types
        assert types[-1] == "done"
        assert isinstance(events[-1]["chips"], list) and events[-1]["chips"]


# ── 5. send message (v1) ────────────────────────────────────────────────────


class TestSendMessageV1:
    def test_emits_sheet_update_before_done(self, client, ai):
        # Make the v1 extractor return fields the software pathway recognizes.
        ai["sheet_extract"] = {
            "problem": "Home cooks waste food and time planning meals",
            "audience": "Busy home cooks",
        }
        pid = _make_v1_project(client)
        sid = _start_session(client, pid)

        resp = client.post(
            f"/api/v1/discovery/{sid}/message",
            json={"content": "It's a meal planning app for busy home cooks."},
        )
        assert resp.status_code == 200, resp.text
        events = parse_sse(resp.text)
        types = event_types(events)

        assert "token" in types
        assert "sheet_update" in types
        assert "field_update" not in types, "v1 must not emit the v2 field event"
        assert types[-1] == "done"
        assert types.index("sheet_update") < types.index("done")

        sheet = next(e for e in events if e["type"] == "sheet_update")["sheet"]
        assert sheet["problem"] == "Home cooks waste food and time planning meals"
        assert sheet["audience"] == "Busy home cooks"
        assert "confidence_score" in sheet

    def test_no_extracted_fields_skips_sheet_update_but_emits_done(self, client, ai):
        ai["sheet_extract"] = {}  # nothing extracted → sheet unchanged
        pid = _make_v1_project(client)
        sid = _start_session(client, pid)

        resp = client.post(
            f"/api/v1/discovery/{sid}/message",
            json={"content": "hello"},
        )
        events = parse_sse(resp.text)
        types = event_types(events)
        assert "sheet_update" not in types
        assert types[-1] == "done"


# ── 6. flow-version prompt branching ────────────────────────────────────────


class TestFlowVersionPromptBranching:
    def test_v2_message_uses_unified_prompt_marker(self, client, ai):
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)
        client.post(f"/api/v1/discovery/{sid}/message", json={"content": "hi"})
        prompt = ai["captured"]["system_prompts"][-1]
        # Stable marker emitted by build_unified_discovery_prompt.
        assert "MODULES IN THIS DESIGN KIT" in prompt

    def test_v1_message_prompt_lacks_unified_marker(self, client, ai):
        pid = _make_v1_project(client)
        sid = _start_session(client, pid)
        client.post(f"/api/v1/discovery/{sid}/message", json={"content": "hi"})
        prompt = ai["captured"]["system_prompts"][-1]
        assert "MODULES IN THIS DESIGN KIT" not in prompt

    def test_message_history_passed_to_stream(self, client, ai):
        """The stream is invoked with the persisted user turn in its history."""
        pid = _make_v2_project(client)
        sid = _start_session(client, pid)
        client.post(
            f"/api/v1/discovery/{sid}/message",
            json={"content": "my unique idea sentinel"},
        )
        msgs = ai["captured"]["stream_messages"][-1]
        assert any(
            m["role"] == "user" and "my unique idea sentinel" in m["content"]
            for m in msgs
        )


# ── 7. message edge cases ───────────────────────────────────────────────────


class TestSendMessageEdgeCases:
    def test_message_missing_session_404(self, client, ai):
        resp = client.post(
            f"/api/v1/discovery/{uuid.uuid4()}/message",
            json={"content": "anybody home?"},
        )
        assert resp.status_code == 404
