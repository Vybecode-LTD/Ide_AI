"""
Tests for the Discovery v2 unified-flow code paths.

Covers (audit finding I4):
    1. ``_coerce_field_value`` type coercion (text / longtext / list / dict).
    2. ``_reset_module_library`` cache reset hook (audit L5).
    3. ``compute_field_summary`` aggregation against a seeded ModulePathway +
       ModuleResponse pair.
    4. ``load_decorated_pathway_modules`` tolerates list[str] AND list[dict]
       shapes (migration 030 backfill compatibility).
    5. ``apply_extracted_module_fields`` empty-input path + invalid-key drops.
    6. ``build_unified_discovery_prompt`` mentions every module + REQUIRED /
       optional / filled / missing flags.
    7. ``build_unified_greeting_prompt`` references the assembled module set.

Tests that exercise the PostgreSQL-specific ``ON CONFLICT`` upsert path are
documented as PG-only and skipped under SQLite (the in-memory test harness).
The upsert SQL itself is exercised by the discovery integration tests in
production; these unit tests cover the surrounding logic.
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.project import Project
from app.models.user import User
from app.services import ai_service, discovery_service, modular_pathway_service
from app.services.discovery_service import _coerce_field_value


# ── 1. _coerce_field_value ───────────────────────────────────────────────


class TestCoerceFieldValue:
    """Pure unit tests for type coercion. No DB / AI dependency."""

    # ── text / longtext ──
    def test_text_strips_string(self):
        assert _coerce_field_value("  hello  ", "text") == "hello"

    def test_text_empty_after_strip_returns_none(self):
        assert _coerce_field_value("   ", "text") is None

    def test_text_none_returns_none(self):
        assert _coerce_field_value(None, "text") is None

    def test_text_serializes_list(self):
        # If the AI returns a list for a text field, JSON-serialize it
        assert _coerce_field_value(["a", "b"], "text") == '["a", "b"]'

    def test_text_serializes_dict(self):
        result = _coerce_field_value({"k": "v"}, "text")
        assert result == '{"k": "v"}'

    def test_text_coerces_number(self):
        assert _coerce_field_value(42, "text") == "42"

    def test_longtext_strips_string(self):
        assert _coerce_field_value("  long content  ", "longtext") == "long content"

    # ── list ──
    def test_list_passthrough(self):
        assert _coerce_field_value(["one", "two"], "list") == ["one", "two"]

    def test_list_drops_empty_entries(self):
        assert _coerce_field_value(["one", "", None, "two"], "list") == ["one", "two"]

    def test_list_wraps_string(self):
        # Single string for a list field gets wrapped
        assert _coerce_field_value("solo item", "list") == ["solo item"]

    def test_list_empty_string_returns_none(self):
        assert _coerce_field_value("   ", "list") is None

    def test_list_extracts_dict_values(self):
        assert _coerce_field_value({"a": "one", "b": "two"}, "list") == ["one", "two"]

    def test_list_empty_returns_none(self):
        assert _coerce_field_value([], "list") is None

    # ── dict ──
    def test_dict_passthrough(self):
        d = {"age": "28-45", "location": "US"}
        assert _coerce_field_value(d, "dict") == d

    def test_dict_empty_returns_none(self):
        assert _coerce_field_value({}, "dict") is None

    def test_dict_drops_scalar(self):
        # M7-related: scalar value for dict-typed field is dropped (returns None
        # so caller can log it and skip)
        assert _coerce_field_value("not a dict", "dict") is None
        assert _coerce_field_value(42, "dict") is None
        assert _coerce_field_value(["not", "a", "dict"], "dict") is None

    # ── unknown type ──
    def test_unknown_type_passthrough(self):
        # If a field has an unknown declared type, value passes through unchanged
        assert _coerce_field_value("whatever", "unknown_type") == "whatever"


# ── 2. _reset_module_library ─────────────────────────────────────────────


class TestResetModuleLibrary:
    """L5: tests can reset the lazy-loaded module library cache."""

    def test_reset_forces_reload(self):
        # Touch the cache to populate it
        mods_before = modular_pathway_service._load_modules()
        assert mods_before is not None
        # Override cache with a sentinel
        modular_pathway_service._module_library = [{"id": "test_sentinel"}]
        assert modular_pathway_service._load_modules() == [{"id": "test_sentinel"}]
        # Reset and verify the next call re-reads from disk
        modular_pathway_service._reset_module_library()
        mods_after = modular_pathway_service._load_modules()
        assert mods_after == mods_before
        assert not any(m.get("id") == "test_sentinel" for m in mods_after)

    def test_reset_when_empty_is_noop(self):
        modular_pathway_service._module_library = None
        modular_pathway_service._reset_module_library()  # should not raise
        assert modular_pathway_service._module_library is None


# ── DB fixtures used by sections 3-5 ─────────────────────────────────────


@pytest_asyncio.fixture
async def v2_project(db_session: AsyncSession, test_user: User) -> Project:
    """A v2 project owned by test_user, with no pathway/responses yet."""
    project = Project(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="V2 Test Project",
        description="A test project on the v2 flow",
        platform="web",
        audience="consumers",
        complexity="medium",
        tone="casual",
        accent_color="#00E5FF",
        pathway_id="software_product",
        ai_partner_style="strategist",
        primary_category="software_tech",
        flow_version="v2",
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def seeded_pathway(db_session: AsyncSession, v2_project: Project) -> ModulePathway:
    """A v2 pathway with two real library modules (string IDs, post-030 shape)."""
    pathway = ModulePathway(
        id=uuid.uuid4(),
        project_id=v2_project.id,
        modules=["audience_persona_builder", "problem_opportunity_framer"],
        lite_deep_settings={"audience_persona_builder": "lite", "problem_opportunity_framer": "lite"},
        status="active",
    )
    db_session.add(pathway)
    await db_session.flush()
    return pathway


# ── 3. compute_field_summary ─────────────────────────────────────────────


class TestComputeFieldSummary:
    @pytest.mark.asyncio
    async def test_empty_pathway_returns_zeros(self, db_session, v2_project):
        summary = await discovery_service.compute_field_summary(
            db_session, v2_project.id, modules=[],
        )
        assert summary["total_filled"] == 0
        assert summary["total_fields"] == 0
        assert summary["required_filled"] == 0
        assert summary["required_total"] == 0
        assert summary["overall_percent"] == 0
        assert summary["per_module"] == []

    @pytest.mark.asyncio
    async def test_no_responses_yet(self, db_session, v2_project, seeded_pathway):
        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        summary = await discovery_service.compute_field_summary(
            db_session, v2_project.id, decorated,
        )
        # Two modules from the seeded library, both with field schemas
        assert len(summary["per_module"]) == 2
        # All counts zero since no ModuleResponse rows exist yet
        assert summary["total_filled"] == 0
        assert summary["required_filled"] == 0
        # But the denominators should be non-zero
        assert summary["total_fields"] > 0
        assert summary["required_total"] > 0
        assert summary["overall_percent"] == 0

    @pytest.mark.asyncio
    async def test_partial_responses(self, db_session, v2_project, seeded_pathway):
        # Seed one filled field for audience_persona_builder
        response = ModuleResponse(
            id=uuid.uuid4(),
            project_id=v2_project.id,
            module_id="audience_persona_builder",
            responses={"primary_persona": "SaaS founders aged 28-45"},
            status="active",
        )
        db_session.add(response)
        await db_session.flush()

        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        summary = await discovery_service.compute_field_summary(
            db_session, v2_project.id, decorated,
        )

        assert summary["total_filled"] == 1
        assert summary["required_filled"] == 1  # primary_persona is required
        # Find the audience module in per_module
        audience_module = next(
            m for m in summary["per_module"] if m["module_id"] == "audience_persona_builder"
        )
        assert audience_module["filled"] == 1
        assert audience_module["required_filled"] == 1

    @pytest.mark.asyncio
    async def test_overall_percent_calculation(self, db_session, v2_project, seeded_pathway):
        # Fill ALL fields of one module to exercise the percent math
        decorated_before = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        first_mod = decorated_before[0]
        all_keys = {f["key"]: f"value-{f['key']}" for f in first_mod["fields"]}
        response = ModuleResponse(
            id=uuid.uuid4(),
            project_id=v2_project.id,
            module_id=first_mod["module_id"],
            responses=all_keys,
            status="active",
        )
        db_session.add(response)
        await db_session.flush()

        summary = await discovery_service.compute_field_summary(
            db_session, v2_project.id, decorated_before,
        )
        # The first module is now 100% filled
        first_summary = next(m for m in summary["per_module"] if m["module_id"] == first_mod["module_id"])
        assert first_summary["filled"] == first_summary["total"]
        # Overall percent should be > 0 but < 100 (other module still empty)
        assert 0 < summary["overall_percent"] < 100


# ── 4. load_decorated_pathway_modules ────────────────────────────────────


class TestLoadDecoratedPathwayModules:
    @pytest.mark.asyncio
    async def test_string_shape(self, db_session, v2_project, seeded_pathway):
        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        assert len(decorated) == 2
        for entry in decorated:
            assert "module_id" in entry
            assert "label" in entry
            assert "fields" in entry
            assert isinstance(entry["fields"], list)
            assert "has_output" in entry

    @pytest.mark.asyncio
    async def test_legacy_dict_shape(self, db_session, v2_project):
        # Some pre-migration-030 rows may still store list[dict]
        pathway = ModulePathway(
            id=uuid.uuid4(),
            project_id=v2_project.id,
            modules=[{"module_id": "audience_persona_builder", "label": "X"}],
            lite_deep_settings={},
            status="active",
        )
        db_session.add(pathway)
        await db_session.flush()

        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        assert len(decorated) == 1
        assert decorated[0]["module_id"] == "audience_persona_builder"

    @pytest.mark.asyncio
    async def test_unknown_module_ids_skipped(self, db_session, v2_project):
        pathway = ModulePathway(
            id=uuid.uuid4(),
            project_id=v2_project.id,
            modules=["nonexistent_module", "audience_persona_builder"],
            lite_deep_settings={},
            status="active",
        )
        db_session.add(pathway)
        await db_session.flush()

        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        # Only the real one survives
        assert len(decorated) == 1
        assert decorated[0]["module_id"] == "audience_persona_builder"

    @pytest.mark.asyncio
    async def test_no_pathway_returns_empty(self, db_session, v2_project):
        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        assert decorated == []


# ── 5. apply_extracted_module_fields (non-PG path) ───────────────────────


class TestApplyExtractedModuleFields:
    """The PG-specific ON CONFLICT upsert is not exercised under SQLite — see
    the module docstring. These tests cover the validation logic that runs
    BEFORE the upsert."""

    @pytest.mark.asyncio
    async def test_empty_extracted_returns_empty_updates(
        self, db_session, v2_project, seeded_pathway
    ):
        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        updates, summary = await discovery_service.apply_extracted_module_fields(
            db_session, v2_project.id, extracted={}, modules=decorated,
        )
        assert updates == []
        # Summary still computed
        assert "overall_percent" in summary
        assert summary["overall_percent"] == 0

    @pytest.mark.asyncio
    async def test_invalid_keys_dropped(self, db_session, v2_project, seeded_pathway):
        decorated = await discovery_service.load_decorated_pathway_modules(
            db_session, v2_project.id,
        )
        # Keys without a "." separator, unknown modules, unknown fields — all dropped.
        # ALL of these should drop BEFORE the upsert runs, so this test works on
        # SQLite even though the ON CONFLICT statement requires PostgreSQL.
        extracted = {
            "no_dot_separator": "ignored",
            "unknown_module.field": "ignored",
            "audience_persona_builder.totally_made_up_key": "ignored",
            "": "ignored",
        }
        updates, _ = await discovery_service.apply_extracted_module_fields(
            db_session, v2_project.id, extracted=extracted, modules=decorated,
        )
        # Every key dropped — no updates emitted, no upsert attempted.
        assert updates == []


# ── 6. build_unified_discovery_prompt ────────────────────────────────────


class TestBuildUnifiedDiscoveryPrompt:
    @pytest.mark.asyncio
    async def test_prompt_lists_all_modules(self):
        modules = [
            {
                "module_id": "audience_persona_builder",
                "label": "Audience & Persona Builder",
                "fields": [
                    {"key": "primary_persona", "type": "text", "required": True, "extraction_hint": "..."},
                    {"key": "motivations", "type": "list", "required": False, "extraction_hint": "..."},
                ],
            },
            {
                "module_id": "problem_opportunity_framer",
                "label": "Problem / Opportunity Framer",
                "fields": [
                    {"key": "core_problem", "type": "longtext", "required": True, "extraction_hint": "..."},
                ],
            },
        ]
        prompt = await ai_service.build_unified_discovery_prompt(
            project_name="Test",
            project_description="A test idea",
            primary_category="software_tech",
            platform="web",
            modules=modules,
            current_fields={},
        )
        # Project header
        assert "Test" in prompt
        assert "software_tech" in prompt
        # Both modules and labels appear
        assert "Audience & Persona Builder" in prompt
        assert "Problem / Opportunity Framer" in prompt
        # Field keys appear
        assert "primary_persona" in prompt
        assert "motivations" in prompt
        assert "core_problem" in prompt
        # Module count rendered
        assert "MODULES IN THIS DESIGN KIT (2)" in prompt
        # Discovery rules block present
        assert "DISCOVERY RULES" in prompt
        # Chips section present
        assert "[CHIPS:" in prompt

    @pytest.mark.asyncio
    async def test_required_vs_optional_marked(self):
        modules = [{
            "module_id": "m1",
            "label": "M1",
            "fields": [
                {"key": "req_field", "type": "text", "required": True, "extraction_hint": ""},
                {"key": "opt_field", "type": "text", "required": False, "extraction_hint": ""},
            ],
        }]
        prompt = await ai_service.build_unified_discovery_prompt(
            project_name="t", project_description=None, primary_category=None,
            platform=None, modules=modules, current_fields={},
        )
        # The schema rendering includes the REQUIRED keyword for required fields
        assert "REQUIRED" in prompt
        # And "optional" (lowercase per the format string in ai_service)
        assert "optional" in prompt

    @pytest.mark.asyncio
    async def test_filled_status_marked(self):
        modules = [{
            "module_id": "m1",
            "label": "M1",
            "fields": [
                {"key": "k1", "type": "text", "required": True, "extraction_hint": ""},
                {"key": "k2", "type": "text", "required": True, "extraction_hint": ""},
            ],
        }]
        current_fields = {"m1": {"k1": "already filled"}}
        prompt = await ai_service.build_unified_discovery_prompt(
            project_name="t", project_description=None, primary_category=None,
            platform=None, modules=modules, current_fields=current_fields,
        )
        # k1 should be marked as filled
        assert "STATUS: filled" in prompt
        # k2 should be marked as missing
        assert "STATUS: missing" in prompt


# ── 7. build_unified_greeting_prompt ─────────────────────────────────────


class TestBuildUnifiedGreetingPrompt:
    @pytest.mark.asyncio
    async def test_references_modules(self):
        modules = [
            {"module_id": "audience_persona_builder", "label": "Audience & Persona Builder",
             "fields": [{"key": "primary_persona", "type": "text", "required": True, "extraction_hint": "describe the persona"}]},
            {"module_id": "problem_opportunity_framer", "label": "Problem / Opportunity Framer",
             "fields": []},
        ]
        prompt = await ai_service.build_unified_greeting_prompt(
            project_name="Project X",
            project_description="A bold idea",
            primary_category="software_tech",
            platform="web",
            modules=modules,
        )
        # Module count rendered
        assert "MODULES IN THIS DESIGN KIT (2 total)" in prompt
        # At least the first module's label appears in the preview line
        assert "Audience & Persona Builder" in prompt
        # First module's extraction hint steers the opening question
        assert "describe the persona" in prompt
        # Chips block present
        assert "[CHIPS:" in prompt

    @pytest.mark.asyncio
    async def test_empty_modules_falls_back_to_legacy(self):
        # Falls back to the legacy greeting prompt when modules is empty
        prompt = await ai_service.build_unified_greeting_prompt(
            project_name="Project X",
            project_description="A bold idea",
            primary_category=None,
            platform="web",
            modules=[],
        )
        # The legacy greeting has a different shape — no "MODULES IN THIS DESIGN KIT"
        # but should still produce a non-empty prompt with chips guidance
        assert prompt
        assert "MODULES IN THIS DESIGN KIT" not in prompt
        assert "CHIPS" in prompt

    @pytest.mark.asyncio
    async def test_more_than_5_modules_truncated_in_preview(self):
        modules = [
            {"module_id": f"m{i}", "label": f"Module {i}",
             "fields": [{"key": "k", "type": "text", "required": True, "extraction_hint": ""}]}
            for i in range(8)
        ]
        prompt = await ai_service.build_unified_greeting_prompt(
            project_name="X", project_description=None,
            primary_category=None, platform=None, modules=modules,
        )
        # Preview line should show "plus 3 more" (8 total - 5 shown)
        assert "plus 3 more" in prompt


# ── 7. Session resume regression (audit fix verification) ──────────────


class TestSessionResumeRegression:
    """Regression tests for the scope-aware session resume logic.

    Verifies that the `scope_module_ids.is_(None)` filters added to
    `get_latest_active_session_for_project` and the orphan cleanup don't
    break the non-scoped (main-flow) paths.
    """

    @pytest.mark.asyncio
    async def test_resume_returns_existing_active_session(self, db_session, v2_project):
        """Basic resume: second call returns the same session."""
        s1, created1 = await discovery_service.create_or_resume_session(
            db_session, v2_project.id,
        )
        assert created1 is True

        s2, created2 = await discovery_service.create_or_resume_session(
            db_session, v2_project.id,
        )
        assert created2 is False
        assert s2.id == s1.id

    @pytest.mark.asyncio
    async def test_scoped_session_always_creates_new(self, db_session, v2_project, seeded_pathway):
        """Scoped calls never resume — each one creates a fresh session."""
        mod_id = seeded_pathway.modules[0]

        s1, c1 = await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )
        assert c1 is True

        s2, c2 = await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )
        assert c2 is True
        assert s2.id != s1.id

    @pytest.mark.asyncio
    async def test_scoped_session_does_not_pollute_main_resume(self, db_session, v2_project, seeded_pathway):
        """Creating scoped sessions doesn't affect main-flow resume."""
        mod_id = seeded_pathway.modules[0]

        # Create main session
        main, _ = await discovery_service.create_or_resume_session(
            db_session, v2_project.id,
        )

        # Create scoped sessions
        await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )
        await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )

        # Main-flow resume should still return the original session
        resumed, created = await discovery_service.create_or_resume_session(
            db_session, v2_project.id,
        )
        assert created is False
        assert resumed.id == main.id

    @pytest.mark.asyncio
    async def test_get_latest_active_ignores_scoped(self, db_session, v2_project, seeded_pathway):
        """get_latest_active_session_for_project never returns a scoped session."""
        mod_id = seeded_pathway.modules[0]

        # Create only scoped sessions — no main session
        await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )
        await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )

        latest = await discovery_service.get_latest_active_session_for_project(
            db_session, v2_project.id,
        )
        assert latest is None

    @pytest.mark.asyncio
    async def test_orphan_cleanup_skips_scoped_sessions(self, db_session, v2_project, seeded_pathway):
        """Empty scoped sessions are NOT abandoned by the orphan cleanup."""
        mod_id = seeded_pathway.modules[0]

        # Create a main session with messages (so it gets selected as best)
        main, _ = await discovery_service.create_or_resume_session(
            db_session, v2_project.id,
        )
        main.messages = [{"role": "assistant", "content": "hi"}]
        await db_session.flush()

        # Create empty scoped sessions (0 messages)
        scoped1, _ = await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )
        scoped2, _ = await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )

        # Trigger resume (which runs orphan cleanup internally)
        await discovery_service.get_latest_active_session_for_project(
            db_session, v2_project.id,
        )
        await db_session.flush()

        # Scoped sessions should still be active — NOT abandoned
        await db_session.refresh(scoped1)
        await db_session.refresh(scoped2)
        assert scoped1.status == "active"
        assert scoped2.status == "active"

    @pytest.mark.asyncio
    async def test_force_new_still_works_alongside_scoped(self, db_session, v2_project, seeded_pathway):
        """force_new creates a new main-flow session even when scoped sessions exist."""
        mod_id = seeded_pathway.modules[0]

        # Create main + scoped sessions
        main, _ = await discovery_service.create_or_resume_session(
            db_session, v2_project.id,
        )
        await discovery_service.create_or_resume_session(
            db_session, v2_project.id, scope_module_ids=[mod_id],
        )

        # force_new should create a new main session
        forced, created = await discovery_service.create_or_resume_session(
            db_session, v2_project.id, force_new=True,
        )
        assert created is True
        assert forced.id != main.id
        assert forced.scope_module_ids is None
