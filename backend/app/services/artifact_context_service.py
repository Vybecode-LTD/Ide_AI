"""
artifact_context_service.py — Canonical v1/v2 artifact context builder.

Provides a single ``build_artifact_context()`` function that downstream
consumers (exports, blocks, pipeline, prompt kit, market, sprint) use
to get the full project knowledge regardless of flow version:

- **v1 projects**: context is assembled from the ``design_sheets`` table
  (the legacy extraction target).
- **v2 projects**: context is assembled from ``module_responses`` rows +
  module library field schemas via ``load_decorated_pathway_modules()``.

Also provides ``context_for_ai()`` for producing a flat text summary
suitable for injection into AI prompts (block generation, pipeline
recommendation, etc.).
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.models.design_sheet import DesignSheet
from app.models.module_response import ModuleResponse
from app.models.pipeline_node import PipelineNode
from app.models.project import Project


# ── helpers ──────────────────────────────────────────────────────────


def _value_text(value: Any) -> str:
    """Convert an arbitrary field value to a human-readable string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _module_summary(modules: list[dict[str, Any]]) -> str:
    """Build a Markdown-style summary of all module responses.

    Used as ``discovery_summary`` in the context dict — a single text block
    that downstream AI consumers can treat as the "project brief".
    """
    lines: list[str] = []
    for mod in modules:
        label = mod.get("label") or mod.get("module_id")
        responses = mod.get("responses") or {}
        if not responses:
            continue
        lines.append(f"## {label}")
        fields = {f.get("key"): f for f in mod.get("fields", []) if f.get("key")}
        for key, value in responses.items():
            if key.startswith("__"):
                continue
            text = _value_text(value)
            if not text:
                continue
            field = fields.get(key, {})
            lines.append(f"- {field.get('label') or key}: {text}")
    return "\n".join(lines)


# ── public API ───────────────────────────────────────────────────────


async def build_artifact_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Return a unified context dict for a project.

    The dict is intentionally a plain dict (not an ORM model) so downstream
    services can consume it without importing model classes.

    Keys always present:
        flow_version, project, project_name, project_description,
        platform, audience, tone, complexity,
        problem, mvp, features, tech_constraints, success_metric,
        confidence_score, sheet, blocks, pipeline,
        modules, discovery_summary

    v1 projects: ``modules`` is empty, values come from ``sheet``.
    v2 projects: ``modules`` is populated from module_responses + library,
    ``discovery_summary`` is a Markdown text assembled from responses,
    and sheet-level keys are back-filled from module data where available.
    """
    # ── project + ownership ──────────────────────────────────────────
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # ── design sheet (always fetched — may be empty for v2) ──────────
    sheet_result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    sheet = sheet_result.scalar_one_or_none()

    # ── blocks + pipeline (shared by both flows) ─────────────────────
    blocks_result = await db.execute(
        select(Block).where(Block.project_id == project_id).order_by(Block.order)
    )
    blocks = list(blocks_result.scalars().all())

    pipeline_result = await db.execute(
        select(PipelineNode).where(PipelineNode.project_id == project_id)
    )
    pipeline = list(pipeline_result.scalars().all())

    # ── base context ────────────────────────────────────────────────
    # Priority: sheet values > project-level values > fallback.
    # This matches the existing ``build_sheet_context`` in market_service.
    context: dict[str, Any] = {
        "project": project,
        "sheet": sheet,
        "blocks": blocks,
        "pipeline": pipeline,
        "flow_version": getattr(project, "flow_version", "v1"),
        "project_name": project.name,
        "project_description": project.description or "",
        "platform": (sheet.platform if sheet else None) or project.platform or "custom",
        "audience": (sheet.audience if sheet else None) or project.audience or "",
        "tone": (sheet.tone if sheet else None) or project.tone or "",
        "complexity": project.complexity or "medium",
        "problem": (sheet.problem if sheet else None) or "",
        "mvp": (sheet.mvp if sheet else None) or "",
        "features": (sheet.features if sheet else None) or [],
        "tech_constraints": (sheet.tech_constraints if sheet else None) or "",
        "success_metric": (sheet.success_metric if sheet else None) or "",
        "confidence_score": sheet.confidence_score if sheet else 0,
        "modules": [],
        "discovery_summary": "",
    }

    # ── v2 enrichment from module responses ──────────────────────────
    if getattr(project, "flow_version", "v1") == "v2":
        from app.services.discovery_service import load_decorated_pathway_modules

        decorated = await load_decorated_pathway_modules(db, project_id)

        response_result = await db.execute(
            select(ModuleResponse).where(ModuleResponse.project_id == project_id)
        )
        responses = {r.module_id: r for r in response_result.scalars().all()}

        modules: list[dict[str, Any]] = []
        for mod in decorated:
            response = responses.get(mod["module_id"])
            modules.append({
                **mod,
                "responses": dict(response.responses or {}) if response else {},
                "status": response.status if response else "pending",
            })

        context["modules"] = modules
        context["discovery_summary"] = _module_summary(modules)

        # Back-fill sheet-level keys so downstream consumers that check
        # context["problem"] etc. get something useful even without a
        # DesignSheet row.
        if not context["problem"]:
            context["problem"] = context["discovery_summary"]

    return context


def context_for_ai(context: dict[str, Any]) -> str:
    """Produce a flat text summary from context for AI prompt injection.

    Used when generating blocks, pipeline recommendations, prompts, etc.
    For v1, summarises the design sheet fields. For v2, includes the full
    module-level discovery summary.
    """
    parts = [
        f"Project: {context.get('project_name', '')}",
        f"Description: {context.get('project_description', '')}",
        f"Platform: {context.get('platform', '')}",
        f"Audience: {context.get('audience', '')}",
        f"Tone: {context.get('tone', '')}",
        f"Complexity: {context.get('complexity', '')}",
    ]

    # v1: sheet fields
    if context.get("flow_version") != "v2":
        if context.get("problem"):
            parts.append(f"Problem: {context['problem']}")
        if context.get("mvp"):
            parts.append(f"MVP: {context['mvp']}")
        if context.get("features"):
            parts.append(f"Features: {json.dumps(context['features'], ensure_ascii=False)}")
        if context.get("tech_constraints"):
            parts.append(f"Tech constraints: {context['tech_constraints']}")
        if context.get("success_metric"):
            parts.append(f"Success metric: {context['success_metric']}")
    else:
        # v2: module discovery summary
        summary = context.get("discovery_summary") or ""
        if summary:
            parts.append("")
            parts.append(summary)

    return "\n".join(p for p in parts if p is not None).strip()
