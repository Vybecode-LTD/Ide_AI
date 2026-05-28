"""
sheet_service.py — Design sheet auto-fill and block generation logic.
Extracts structured data from AI responses and generates feature blocks.
Block generation prompt and categories are driven by the active PathwayConfig.
"""
from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.block import Block
from app.models.design_sheet import DesignSheet
from app.services.ai_service import client

if TYPE_CHECKING:
    from app.pathways.base import PathwayConfig


def _get_pathway(pathway: PathwayConfig | None = None) -> PathwayConfig:
    """Resolve a pathway, falling back to software_product."""
    if pathway is not None:
        return pathway
    from app.pathways import PathwayRegistry
    return PathwayRegistry.get("software_product")


def _build_sheet_context(sheet: DesignSheet, pathway: PathwayConfig) -> dict[str, str]:
    """Build a context dict from the sheet for prompt formatting."""
    ctx: dict[str, str] = {}
    for sf in pathway.sheet_fields:
        val = getattr(sheet, sf.key, None)
        if not val and sheet.fields_data:
            val = sheet.fields_data.get(sf.key)
        if isinstance(val, (list, dict)):
            ctx[sf.key] = json.dumps(val)
        else:
            ctx[sf.key] = str(val) if val else "Not specified"
    return ctx


async def _generate_blocks_from_prompt_context(
    db: AsyncSession,
    ctx: dict[str, str],
    project_id: uuid.UUID,
    pw: "PathwayConfig",
) -> list[Block]:
    """Shared block generation: format prompt, call Claude, create Block rows."""
    try:
        prompt = pw.block_generation_prompt.format(**ctx)
    except KeyError:
        prompt = pw.block_generation_prompt
        for k, v in ctx.items():
            prompt = prompt.replace(f"{{{k}}}", v)

    valid_categories = {c.id for c in pw.block_categories}
    default_category = pw.block_categories[0].id if pw.block_categories else "core"

    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2048,
        system="You are a product feature generator. Return only valid JSON arrays.",
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        block_data = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        block_data = []

    blocks = []
    for i, bd in enumerate(block_data):
        cat = bd.get("category", default_category)
        if cat not in valid_categories:
            cat = default_category

        block = Block(
            project_id=project_id,
            name=bd.get("name", f"Feature {i+1}"),
            description=bd.get("description", ""),
            category=cat,
            priority=bd.get("priority", pw.block_priorities[0] if pw.block_priorities else "mvp"),
            effort=bd.get("effort", pw.block_efforts[1] if len(pw.block_efforts) > 1 else "M"),
            order=i,
            is_mvp=bd.get("priority", "mvp") == (pw.block_priorities[0] if pw.block_priorities else "mvp"),
        )
        db.add(block)
        blocks.append(block)

    await db.flush()
    return blocks


async def generate_blocks(
    db: AsyncSession,
    sheet: DesignSheet,
    project_id: uuid.UUID,
    pathway: PathwayConfig | None = None,
) -> list[Block]:
    """Generate feature blocks from a completed design sheet using Claude.

    Uses the pathway's ``block_generation_prompt`` and ``block_categories``
    to produce domain-appropriate blocks.
    """
    pw = _get_pathway(pathway)
    ctx = _build_sheet_context(sheet, pw)
    return await _generate_blocks_from_prompt_context(db, ctx, project_id, pw)


async def generate_blocks_from_context(
    db: AsyncSession,
    artifact_ctx: dict,
    project_id: uuid.UUID,
    pathway: PathwayConfig | None = None,
) -> list[Block]:
    """Generate feature blocks from a unified artifact context (v2 projects).

    Builds the same prompt context dict from the artifact context instead
    of a DesignSheet ORM object, then delegates to the shared generator.
    """
    pw = _get_pathway(pathway)
    ctx: dict[str, str] = {}
    for sf in pw.sheet_fields:
        val = artifact_ctx.get(sf.key)
        if isinstance(val, (list, dict)):
            ctx[sf.key] = json.dumps(val)
        else:
            ctx[sf.key] = str(val) if val else "Not specified"
    # For v2, enrich the problem field with the full discovery summary
    if artifact_ctx.get("discovery_summary"):
        ctx["problem"] = artifact_ctx["discovery_summary"]
    return await _generate_blocks_from_prompt_context(db, ctx, project_id, pw)


def extract_fields(ai_response: str) -> dict:
    """Extract design sheet fields from a single AI response message.
    This is a lightweight local extraction (no API call)."""
    fields = {}
    lower = ai_response.lower()

    # Simple heuristic extraction for common patterns
    if "problem" in lower and ":" in ai_response:
        # Look for structured output patterns
        pass

    return fields
