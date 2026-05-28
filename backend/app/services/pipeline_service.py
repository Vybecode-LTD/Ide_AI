"""
pipeline_service.py — Tech stack / domain-layer recommendation engine.
Provides curated tool options, cost estimation, and compatibility checking.
Domain layers are driven by the active PathwayConfig.
"""
from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.design_sheet import DesignSheet
from app.models.pipeline_node import PipelineNode
from app.services.ai_service import client

if TYPE_CHECKING:
    from app.pathways.base import PathwayConfig


def _get_pathway(pathway: PathwayConfig | None = None) -> PathwayConfig:
    """Resolve a pathway, falling back to software_product."""
    if pathway is not None:
        return pathway
    from app.pathways import PathwayRegistry
    return PathwayRegistry.get("software_product")


RECOMMENDATION_PROMPT = """Based on this product design, recommend the best tech stack.

Design Sheet:
- Problem: {problem}
- Audience: {audience}
- Platform preference: {platform}
- Complexity: {complexity}
- Features: {features}

Available layers and tools:
{layer_options}

For each layer, pick the best tool and explain why in 1 sentence.
Return as JSON array: [{{"layer": "...", "selected_tool": "...", "reason": "..."}}]
Only return valid JSON, no markdown."""


async def recommend_pipeline(
    db: AsyncSession,
    sheet: DesignSheet | None = None,
    project_id: uuid.UUID | None = None,
    complexity: str = "medium",
    pathway: PathwayConfig | None = None,
    *,
    artifact_ctx: dict | None = None,
) -> tuple[list[PipelineNode], list[str], dict]:
    """Recommend a tech pipeline based on design sheet or artifact context.

    Returns (nodes, reasoning_bullets, cost_estimate).
    Uses the pathway's ``domain_layers`` for available tools/costs.

    For v2 projects pass ``artifact_ctx`` instead of ``sheet``; the
    discovery summary is used as the problem description.
    """
    pw = _get_pathway(pathway)
    layers = pw.domain_layers

    if artifact_ctx is not None:
        features_str = json.dumps(artifact_ctx.get("features") or [])
        problem = artifact_ctx.get("discovery_summary") or artifact_ctx.get("problem") or "Not specified"
        audience = artifact_ctx.get("audience") or "Not specified"
        platform = artifact_ctx.get("platform") or "Not specified"
    else:
        features_str = json.dumps(sheet.features or []) if sheet else "[]"
        problem = (sheet.problem if sheet else None) or "Not specified"
        audience = (sheet.audience if sheet else None) or "Not specified"
        platform = (sheet.platform if sheet else None) or "Not specified"

    layer_str = "\n".join(
        f"- {layer}: {', '.join(info['tools'])}"
        for layer, info in layers.items()
    )

    prompt = RECOMMENDATION_PROMPT.format(
        problem=problem,
        audience=audience,
        platform=platform,
        complexity=complexity,
        features=features_str,
        layer_options=layer_str,
    )

    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2048,
        system="You are a tech stack advisor. Return only valid JSON arrays.",
        messages=[{"role": "user", "content": prompt}],
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        recommendations = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        recommendations = [
            {"layer": layer, "selected_tool": info["tools"][0], "reason": "Default recommendation"}
            for layer, info in layers.items()
        ]

    # Delete existing nodes
    await db.execute(delete(PipelineNode).where(PipelineNode.project_id == project_id))

    # Create nodes
    nodes = []
    reasoning = []
    for rec in recommendations:
        layer = rec.get("layer", "")
        tool = rec.get("selected_tool", "")
        reason = rec.get("reason", "")

        if layer in layers:
            node = PipelineNode(
                project_id=project_id,
                layer=layer,
                selected_tool=tool,
                config={"reason": reason},
            )
            db.add(node)
            nodes.append(node)
            reasoning.append(f"{layer}: {tool} — {reason}")

    await db.flush()

    cost_est = estimate_cost_from_nodes(nodes, pathway=pw)
    return nodes, reasoning, cost_est


def estimate_cost(
    pipeline_nodes: list[PipelineNode],
    pathway: PathwayConfig | None = None,
) -> dict:
    """Estimate monthly cost range for a pipeline configuration."""
    return estimate_cost_from_nodes(pipeline_nodes, pathway=pathway)


def estimate_cost_from_nodes(
    nodes: list[PipelineNode],
    pathway: PathwayConfig | None = None,
) -> dict:
    """Calculate cost estimates from pipeline nodes."""
    pw = _get_pathway(pathway)
    layers = pw.domain_layers

    total_min = 0
    total_max = 0
    breakdown = []

    for node in nodes:
        layer_info = layers.get(node.layer, {})
        costs = layer_info.get("costs", {})
        tool_cost = costs.get(node.selected_tool, (0, 50))
        total_min += tool_cost[0]
        total_max += tool_cost[1]
        breakdown.append({
            "layer": node.layer,
            "tool": node.selected_tool,
            "min": tool_cost[0],
            "max": tool_cost[1],
        })

    return {
        "monthly_min": total_min,
        "monthly_max": total_max,
        "breakdown": breakdown,
    }


def check_compatibility(nodes: list[PipelineNode]) -> list[str]:
    """Check compatibility between selected pipeline tools."""
    warnings = []
    tools = {n.layer: n.selected_tool for n in nodes}

    # Check known incompatibilities
    if tools.get("frontend") == "Bubble" and tools.get("backend") not in ("Bubble Backend", None):
        warnings.append("Bubble works best with its built-in backend. External backend adds complexity.")

    if tools.get("database") == "Firebase Firestore" and tools.get("backend") == "FastAPI":
        warnings.append("Firebase Firestore has limited Python support. Consider Supabase Postgres instead.")

    return warnings
