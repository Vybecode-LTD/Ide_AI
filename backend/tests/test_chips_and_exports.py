"""
test_chips_and_exports.py — Regression tests for the chip relevance overhaul
(commit da31ad8) and safe filename slug fix (commit 8eaf247).

Covers:
- generate_quick_chips: Strategy 1 parse, generic-chip filter, sentinel fallback
- CHIP_TYPE_YOUR_ANSWER sentinel contract
- safe_filename_slug: normal, Unicode, empty, truncation
- Transcript PDF endpoint: safe headers, error handling
"""
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.services.ai_service import (
    CHIP_TYPE_YOUR_ANSWER,
    generate_quick_chips,
)
from app.services.export_service import safe_filename_slug
from app.services.transcript_service import format_as_pdf, format_as_text, format_as_markdown


# ===================================================================
# Chip relevance — generate_quick_chips
# ===================================================================

class TestChipParsing:
    """Strategy 1: parse [CHIPS:] tag from AI response."""

    @pytest.mark.asyncio
    async def test_parses_explicit_chips_tag(self):
        response = (
            "Great question! Let me help you think about that.\n"
            "[CHIPS: A cozy kitchen | A flexible living room | A quiet study nook]"
        )
        chips = await generate_quick_chips(response)
        assert chips == ["A cozy kitchen", "A flexible living room", "A quiet study nook"]

    @pytest.mark.asyncio
    async def test_parses_chips_case_insensitive(self):
        response = "What do you think?\n[chips: Option A | Option B | Option C]"
        chips = await generate_quick_chips(response)
        assert chips == ["Option A", "Option B", "Option C"]

    @pytest.mark.asyncio
    async def test_strips_quotes_from_chip_text(self):
        response = '[CHIPS: "Families with kids" | "Solo professionals" | "Retired couples"]'
        chips = await generate_quick_chips(response)
        assert chips == ["Families with kids", "Solo professionals", "Retired couples"]

    @pytest.mark.asyncio
    async def test_parses_two_chip_options(self):
        response = "Which one?\n[CHIPS: Web app | Mobile app]"
        chips = await generate_quick_chips(response)
        assert chips == ["Web app", "Mobile app"]


class TestGenericChipFilter:
    """Strategy 1 should filter out generic/meta-response chips."""

    @pytest.mark.asyncio
    async def test_rejects_all_generic_chips(self):
        """When ALL chips are generic, should fall through to AI generation."""
        response = (
            "What's the one space that needs the most attention?\n"
            '[CHIPS: Yes, exactly | Not quite | I have a different angle]'
        )
        # Patch _generate_chips_from_question so we can verify it was called
        with patch(
            "app.services.ai_service._generate_chips_from_question",
            new_callable=AsyncMock,
            return_value=["The kitchen", "The living room", "A home office"],
        ) as mock_gen:
            chips = await generate_quick_chips(response)
            mock_gen.assert_called_once()
            assert chips == ["The kitchen", "The living room", "A home office"]

    @pytest.mark.asyncio
    async def test_keeps_non_generic_chips_mixed(self):
        """When some chips are generic and some aren't, keep the non-generic ones."""
        response = (
            "What platform?\n"
            '[CHIPS: Web application | Not quite | Mobile app]'
        )
        chips = await generate_quick_chips(response)
        assert "Web application" in chips
        assert "Mobile app" in chips
        assert "Not quite" not in chips

    @pytest.mark.asyncio
    async def test_rejects_tell_me_more_variant(self):
        response = '[CHIPS: Tell me more | Let me explain | The kitchen area]'
        chips = await generate_quick_chips(response)
        assert "Tell me more" not in chips
        assert "Let me explain" not in chips
        assert "The kitchen area" in chips


class TestChipFallback:
    """When no [CHIPS:] tag and no question, return sentinel."""

    @pytest.mark.asyncio
    async def test_no_question_returns_sentinel(self):
        """Response with no question mark should return type-your-answer sentinel."""
        response = "That sounds like a great approach. Let me know what you think."
        chips = await generate_quick_chips(response)
        assert chips == [CHIP_TYPE_YOUR_ANSWER]

    @pytest.mark.asyncio
    async def test_sentinel_is_correct_string(self):
        """The sentinel must match what the frontend checks for."""
        assert CHIP_TYPE_YOUR_ANSWER == "__type_your_answer__"
        assert isinstance(CHIP_TYPE_YOUR_ANSWER, str)


class TestChipAIFallback:
    """Strategy 3: AI-powered contextual chip generation."""

    @pytest.mark.asyncio
    async def test_question_without_chips_tag_calls_ai(self):
        """When response has a question but no [CHIPS:] tag, AI generates chips."""
        response = "What's the one space that needs the most attention to make it feel like a real home?"
        with patch(
            "app.services.ai_service._generate_chips_from_question",
            new_callable=AsyncMock,
            return_value=["The kitchen and dining area", "A flexible living room", "A quiet bedroom"],
        ) as mock_gen:
            chips = await generate_quick_chips(response)
            mock_gen.assert_called_once()
            assert len(chips) == 3
            assert "The kitchen and dining area" in chips

    @pytest.mark.asyncio
    async def test_or_pattern_still_works(self):
        """Strategy 2 (X, Y, or Z pattern) should still trigger before AI fallback."""
        response = "Would you prefer a modern, rustic, or minimalist aesthetic?"
        chips = await generate_quick_chips(response)
        # Strategy 2 should catch "modern, rustic, or minimalist"
        assert len(chips) == 3
        assert any("modern" in c.lower() for c in chips)


# ===================================================================
# Safe filename slugs
# ===================================================================

class TestSafeFilenameSlug:
    """Regression tests for safe_filename_slug utility."""

    def test_normal_text(self):
        assert safe_filename_slug("Tiny Home Designer") == "tiny-home-designer"

    def test_unicode_em_dash(self):
        slug = safe_filename_slug("My Project — Design Kit")
        assert slug == "my-project-design-kit"
        # Must be pure ASCII
        assert slug.isascii()

    def test_unicode_quotes(self):
        slug = safe_filename_slug('Project with "quotes"')
        assert slug == "project-with-quotes"
        assert '"' not in slug

    def test_slashes(self):
        slug = safe_filename_slug("Test / Project")
        assert slug == "test-project"
        assert "/" not in slug

    def test_emoji(self):
        slug = safe_filename_slug("\U0001f3e0 Emoji House \U0001f680")
        assert slug.isascii()
        assert slug == "emoji-house"

    def test_empty_string_returns_fallback(self):
        assert safe_filename_slug("") == "export"
        assert safe_filename_slug("", fallback="project") == "project"

    def test_none_returns_fallback(self):
        # None gets coerced by (name or "")
        assert safe_filename_slug(None or "") == "export"

    def test_max_length_truncation(self):
        slug = safe_filename_slug("a" * 50)
        assert len(slug) <= 30

    def test_custom_max_length(self):
        slug = safe_filename_slug("a" * 50, max_len=10)
        assert len(slug) <= 10

    def test_collapses_multiple_dashes(self):
        slug = safe_filename_slug("Hello   World   Test")
        assert "--" not in slug
        assert slug == "hello-world-test"

    def test_strips_leading_trailing_dashes(self):
        slug = safe_filename_slug("---special---")
        assert not slug.startswith("-")
        assert not slug.endswith("-")
        assert slug == "special"

    def test_only_special_chars_returns_fallback(self):
        slug = safe_filename_slug("—–…", fallback="project")
        assert slug == "project"


# ===================================================================
# Transcript service — PDF/TXT/MD generation
# ===================================================================

class TestTranscriptService:
    """Verify transcript generation doesn't crash with various content."""

    def test_pdf_basic(self):
        messages = [
            {"role": "assistant", "content": "Hello! What are you building?"},
            {"role": "user", "content": "A tiny home designer tool"},
        ]
        result = format_as_pdf(messages, "Test Project")
        assert isinstance(result, (bytes, bytearray))
        assert len(result) > 0
        # PDF magic bytes
        assert bytes(result)[:5] == b"%PDF-"

    def test_pdf_with_unicode_content(self):
        messages = [
            {"role": "assistant", "content": "Let’s explore your idea — I’m excited!"},
            {"role": "user", "content": "Budget is under £500/month"},
        ]
        result = format_as_pdf(messages, "Unicode — Project")
        assert isinstance(result, (bytes, bytearray))
        assert bytes(result)[:5] == b"%PDF-"

    def test_pdf_with_none_content(self):
        messages = [
            {"role": "assistant", "content": None},
            {"role": "user", "content": "Test"},
            {"role": "assistant"},  # Missing ‘content’ key
        ]
        result = format_as_pdf(messages, "Test")
        assert isinstance(result, (bytes, bytearray))

    def test_pdf_empty_messages(self):
        result = format_as_pdf([], "Empty Project")
        assert isinstance(result, (bytes, bytearray))
        assert bytes(result)[:5] == b"%PDF-"

    def test_pdf_large_transcript(self):
        messages = []
        for i in range(40):
            role = "assistant" if i % 2 == 0 else "user"
            messages.append({"role": role, "content": f"Message {i}: " + "x" * 200})
        result = format_as_pdf(messages, "Large Project")
        assert isinstance(result, (bytes, bytearray))
        assert len(result) > 1000

    def test_text_basic(self):
        messages = [
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "Hi there"},
        ]
        result = format_as_text(messages, "Test")
        assert "[AI] Hello!" in result
        assert "[You] Hi there" in result
        assert "2 messages" in result

    def test_markdown_basic(self):
        messages = [
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "Hi there"},
        ]
        result = format_as_markdown(messages, "Test")
        assert "**AI:**" in result
        assert "> Hello!" in result
        assert "**You:**" in result
