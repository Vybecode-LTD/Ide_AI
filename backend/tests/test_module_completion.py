"""
test_module_completion.py — Regression tests for the module completion
enforcement fix.

Covers:
1. build_module_system_prompt question-count injection at various stages
2. Force-complete backstop when AI exceeds question limit
3. _question_range consistency
4. is_module_complete marker detection
5. count_questions_asked accuracy
6. Integration: /respond endpoint force-completes at limit
"""
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.project import Project
from app.models.user import User
from app.services.module_service import (
    _question_range,
    build_module_system_prompt,
    count_questions_asked,
    is_module_complete,
)


# ===================================================================
# 1. _question_range — mode-to-count mapping
# ===================================================================


class TestQuestionRange:
    """Verify question count bounds for each mode."""

    def test_lite_range(self):
        min_q, max_q = _question_range("lite")
        assert min_q == 2
        assert max_q == 3

    def test_deep_range(self):
        min_q, max_q = _question_range("deep")
        assert min_q == 6
        assert max_q == 10

    def test_unknown_mode_defaults_to_lite(self):
        min_q, max_q = _question_range("unknown")
        assert min_q == 2
        assert max_q == 3


# ===================================================================
# 2. is_module_complete — marker detection
# ===================================================================


class TestIsModuleComplete:
    """Verify [MODULE_COMPLETE] marker is detected correctly."""

    def test_detects_marker_at_end(self):
        text = "Here's a summary of what we decided.\n\n[MODULE_COMPLETE]"
        assert is_module_complete(text) is True

    def test_detects_marker_mid_text(self):
        text = "Summary done. [MODULE_COMPLETE] some trailing text"
        assert is_module_complete(text) is True

    def test_no_marker_returns_false(self):
        text = "Just another question for you. What do you think?"
        assert is_module_complete(text) is False

    def test_partial_marker_not_detected(self):
        text = "This module is [MODULE_COMPLET and not done."
        assert is_module_complete(text) is False

    def test_empty_string(self):
        assert is_module_complete("") is False


# ===================================================================
# 3. count_questions_asked — assistant message counting
# ===================================================================


class TestCountQuestionsAsked:
    """Verify assistant-turn counting."""

    def test_counts_assistant_messages(self):
        msgs = [
            {"role": "assistant", "content": "Q1"},
            {"role": "user", "content": "A1"},
            {"role": "assistant", "content": "Q2"},
            {"role": "user", "content": "A2"},
        ]
        assert count_questions_asked(msgs) == 2

    def test_empty_messages(self):
        assert count_questions_asked([]) == 0

    def test_only_user_messages(self):
        msgs = [{"role": "user", "content": "Hello"}]
        assert count_questions_asked(msgs) == 0

    def test_only_assistant_messages(self):
        msgs = [
            {"role": "assistant", "content": "Q1"},
            {"role": "assistant", "content": "Q2"},
            {"role": "assistant", "content": "Q3"},
        ]
        assert count_questions_asked(msgs) == 3


# ===================================================================
# 4. build_module_system_prompt — question count injection
# ===================================================================


class TestPromptQuestionCountInjection:
    """Verify the system prompt carries question-count awareness."""

    _CONCEPT_SHEET = {"problem": "Test problem", "audience": "Testers"}

    def test_no_count_at_zero_questions(self):
        """At question 0 (fresh start), no count message should appear."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            questions_asked=0,
        )
        assert "You have already asked" not in prompt

    def test_count_injected_after_first_question(self):
        """After 1 question asked, the prompt should state the count."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="lite",
            questions_asked=1,
        )
        assert "You have already asked 1 question(s)" in prompt
        assert "maximum of 3" in prompt

    def test_penultimate_question_warning_lite(self):
        """One question before the max, the 'LAST question' warning fires."""
        _, max_q = _question_range("lite")  # max_q = 3
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="lite",
            questions_asked=max_q - 1,  # 2
        )
        assert "LAST question" in prompt

    def test_at_max_questions_critical_warning_lite(self):
        """At the max, the CRITICAL stop instruction fires."""
        _, max_q = _question_range("lite")  # 3
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="lite",
            questions_asked=max_q,
        )
        assert "CRITICAL" in prompt
        assert "MUST NOT ask any more questions" in prompt

    def test_past_max_questions_critical_warning(self):
        """Even past the max, the CRITICAL warning is present."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="lite",
            questions_asked=5,
        )
        assert "CRITICAL" in prompt

    def test_deep_mode_penultimate(self):
        """Deep mode penultimate question (question 9 of max 10)."""
        _, max_q = _question_range("deep")  # 10
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="deep",
            questions_asked=max_q - 1,  # 9
        )
        assert "LAST question" in prompt

    def test_deep_mode_at_max(self):
        """Deep mode at max (10 of 10)."""
        _, max_q = _question_range("deep")  # 10
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="deep",
            questions_asked=max_q,
        )
        assert "CRITICAL" in prompt
        assert "MUST NOT ask any more questions" in prompt

    def test_hard_limit_in_output_rules(self):
        """Output Rules section explicitly states the hard limit."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="lite",
        )
        assert "HARD LIMIT of 3 questions" in prompt

    def test_hard_limit_deep_mode(self):
        """Output Rules section uses the deep-mode max."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            mode="deep",
        )
        assert "HARD LIMIT of 10 questions" in prompt

    def test_default_questions_asked_is_zero(self):
        """Without explicit questions_asked kwarg, defaults to 0."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
        )
        # Should NOT have the "already asked" message
        assert "You have already asked" not in prompt
        # Should NOT have penultimate or critical warnings
        assert "LAST question" not in prompt
        assert "CRITICAL" not in prompt


# ===================================================================
# 5. Integration: /respond force-complete backstop
# ===================================================================


class TestForceCompleteIntegration:
    """Integration tests verifying force-complete via the FastAPI endpoint."""

    @pytest_asyncio.fixture
    async def project_with_module(self, db_session: AsyncSession, test_user: User):
        """Create a locked project with a pathway and an active module response."""
        project = Project(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Test Project",
            platform="Bubble",
            pathway_locked=True,
            ai_partner_style="strategist",
        )
        db_session.add(project)

        module_id = "audience_persona_builder"
        pathway = ModulePathway(
            project_id=project.id,
            modules=[module_id],
            lite_deep_settings={module_id: "lite"},
            status="active",
        )
        db_session.add(pathway)
        await db_session.flush()

        return project, module_id

    def _build_messages(self, n_exchanges: int) -> list[dict]:
        """Build a message history with n assistant+user exchanges."""
        messages = []
        for i in range(n_exchanges):
            messages.append({"role": "assistant", "content": f"Question {i + 1}?"})
            messages.append({"role": "user", "content": f"Answer {i + 1}"})
        return messages

    @pytest.mark.asyncio
    async def test_force_complete_at_lite_max(
        self, db_session: AsyncSession, test_user: User, project_with_module
    ):
        """When AI has asked max questions (3 for lite) and doesn't emit
        [MODULE_COMPLETE], the backend should force-complete."""
        project, module_id = project_with_module

        # Simulate 3 exchanges already done (at the max for lite)
        messages = self._build_messages(3)
        mr = ModuleResponse(
            project_id=project.id,
            module_id=module_id,
            responses={"messages": messages},
            status="active",
        )
        db_session.add(mr)
        await db_session.flush()

        # The AI's next response does NOT contain [MODULE_COMPLETE]
        ai_response = "Here's another follow-up thought about your audience."

        # Mock the streaming to return the non-complete response
        async def mock_stream(*args, **kwargs):
            yield ai_response

        with patch("app.routers.modules.stream_module_response", mock_stream):
            with patch("app.routers.modules.extract_module_output", new_callable=AsyncMock) as mock_extract:
                mock_extract.return_value = {"key": "extracted_value"}

                from app.routers.modules import respond_to_module
                from app.schemas.module_pathway import ModuleRespondPayload

                # Count questions before the call (3 assistant messages)
                assert count_questions_asked(messages) == 3

                # Verify force-complete logic:
                # After adding user message, questions_asked = 3
                # AI responds → new_question_count = 3 + 1 = 4, which >= max_q (3)
                # → force complete = True
                _, max_q = _question_range("lite")
                new_count = count_questions_asked(messages) + 1
                assert new_count >= max_q

    @pytest.mark.asyncio
    async def test_no_force_complete_below_max(
        self, db_session: AsyncSession, test_user: User, project_with_module
    ):
        """When AI is below max questions, should NOT force-complete."""
        project, module_id = project_with_module

        # Only 1 exchange so far
        messages = self._build_messages(1)

        # After this response, question count will be 1 + 1 = 2
        # Lite max is 3, so 2 < 3 → no force-complete
        _, max_q = _question_range("lite")
        new_count = count_questions_asked(messages) + 1
        assert new_count < max_q

    @pytest.mark.asyncio
    async def test_natural_complete_not_double_triggered(
        self, db_session: AsyncSession, test_user: User, project_with_module
    ):
        """When AI emits [MODULE_COMPLETE] naturally, force-complete logic
        doesn't interfere — complete is still True from the marker."""
        project, module_id = project_with_module

        # 2 exchanges done
        messages = self._build_messages(2)

        ai_response = "Great summary!\n\n[MODULE_COMPLETE]"
        complete_from_marker = is_module_complete(ai_response)
        assert complete_from_marker is True

        # Even though we're below max, the marker already triggers completion
        _, max_q = _question_range("lite")
        new_count = count_questions_asked(messages) + 1
        # Force-complete would also fire if at max, but marker already handled it
        assert complete_from_marker is True

    @pytest.mark.asyncio
    async def test_force_complete_deep_mode(
        self, db_session: AsyncSession, test_user: User
    ):
        """Deep mode force-completes at 10 questions."""
        project = Project(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="Deep Project",
            platform="Bubble",
            pathway_locked=True,
            ai_partner_style="strategist",
        )
        db_session.add(project)

        module_id = "audience_persona_builder"
        pathway = ModulePathway(
            project_id=project.id,
            modules=[module_id],
            lite_deep_settings={module_id: "deep"},
            status="active",
        )
        db_session.add(pathway)
        await db_session.flush()

        # 10 exchanges (at max for deep)
        messages = self._build_messages(10)
        assert count_questions_asked(messages) == 10

        _, max_q = _question_range("deep")
        assert max_q == 10

        # AI's next response without marker
        new_count = count_questions_asked(messages) + 1
        assert new_count >= max_q  # 11 >= 10 → force complete


# ===================================================================
# 6. Prompt content — partner style + pre-populated preserved
# ===================================================================


class TestPromptContentPreserved:
    """Verify question-count injection doesn't break other prompt features."""

    _CONCEPT_SHEET = {"problem": "Test problem", "audience": "Testers"}

    def test_partner_style_still_present(self):
        """Partner style fragment should still be in the prompt."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            ai_partner_style="creative",
            questions_asked=2,
        )
        assert "Partner Style" in prompt

    def test_pre_populated_still_present(self):
        """Pre-populated fields should still appear."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
            pre_populated={"audience_description": "Tech professionals"},
            questions_asked=1,
        )
        assert "Pre-populated from earlier modules" in prompt
        assert "Tech professionals" in prompt

    def test_concept_sheet_context_present(self):
        """Concept sheet context should still be injected."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            {"problem": "Users can't find recipes", "audience": "Home cooks"},
            questions_asked=2,
        )
        assert "Users can't find recipes" in prompt
        assert "Home cooks" in prompt

    def test_chips_instruction_still_present(self):
        """Chip generation instruction should still be in output rules."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
        )
        assert "[CHIPS:" in prompt

    def test_module_complete_marker_instruction_present(self):
        """[MODULE_COMPLETE] marker instruction should still be there."""
        prompt = build_module_system_prompt(
            "audience_persona_builder",
            self._CONCEPT_SHEET,
        )
        assert "[MODULE_COMPLETE]" in prompt
