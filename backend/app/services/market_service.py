"""
market_service.py — Market analysis generation engine.
Uses Claude to produce structured market research from design sheet data.
Streams results section-by-section via SSE events.
"""
import json
import uuid
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.design_sheet import DesignSheet
from app.models.market_analysis import MarketAnalysis
from app.models.project import Project
from app.services.ai_service import client


# ---------------------------------------------------------------------------
# Section prompts — each generates one JSON section of the market analysis
# ---------------------------------------------------------------------------

SECTION_SYSTEM = """You are a senior market research analyst with deep expertise in startup strategy, TAM/SAM/SOM modeling, competitive intelligence, and go-to-market planning. You produce data-driven, actionable analysis that reads like a professional consulting report. Return ONLY valid JSON — no markdown, no commentary, no code fences."""

TARGET_MARKET_PROMPT = """Analyze the target market for this product. Use the design sheet data below.

Design Sheet:
{sheet_json}

Return a JSON object with this exact structure:
{{
  "summary": "2-3 sentence market overview",
  "demographics": {{
    "age_range": "e.g. 25-45",
    "income_level": "e.g. $50k-$120k household",
    "education": "e.g. College-educated professionals",
    "location": "e.g. Urban, US/EU tech hubs",
    "gender_split": "e.g. 60/40 male/female"
  }},
  "psychographics": {{
    "values": ["list of core values"],
    "pain_points": ["list of key frustrations"],
    "buying_behavior": "description of how they make purchasing decisions",
    "tech_savviness": "low / medium / high",
    "brand_affinity": "types of brands they gravitate toward"
  }},
  "market_segments": [
    {{
      "name": "segment name",
      "size_pct": 40,
      "description": "who they are and why they matter",
      "priority": "primary / secondary / tertiary"
    }}
  ],
  "user_personas": [
    {{
      "name": "Persona name (e.g. 'Startup Sarah')",
      "role": "their job or life role",
      "goal": "what they want to achieve",
      "frustration": "what blocks them today"
    }}
  ]
}}"""

COMPETITIVE_PROMPT = """Analyze the competitive landscape for this product. Use the design sheet data below.

Design Sheet:
{sheet_json}

Return a JSON object with this exact structure:
{{
  "summary": "2-3 sentence competitive overview",
  "direct_competitors": [
    {{
      "name": "Competitor name",
      "description": "What they do",
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1", "weakness 2"],
      "pricing": "their pricing model/range",
      "market_share_pct": 15,
      "threat_level": "high / medium / low"
    }}
  ],
  "indirect_competitors": [
    {{
      "name": "Competitor name",
      "description": "How they partially solve the same problem",
      "overlap": "where they overlap with this product"
    }}
  ],
  "competitive_advantages": ["list of this product's unique differentiators"],
  "barriers_to_entry": ["list of barriers for new entrants"],
  "market_gaps": ["opportunities competitors are missing"]
}}"""

METRICS_PROMPT = """Generate quantifiable market metrics for this product. Use the design sheet data below.
Provide realistic estimates based on publicly available market data and industry benchmarks.

Design Sheet:
{sheet_json}

Return a JSON object with this exact structure:
{{
  "tam": {{
    "value_usd": 5000000000,
    "description": "Total addressable market explanation",
    "methodology": "How this was estimated"
  }},
  "sam": {{
    "value_usd": 800000000,
    "description": "Serviceable addressable market explanation",
    "methodology": "How this was estimated"
  }},
  "som": {{
    "value_usd": 25000000,
    "description": "Serviceable obtainable market explanation (realistic year 1-3 capture)",
    "methodology": "How this was estimated"
  }},
  "growth_rate_pct": 12.5,
  "growth_trend": "accelerating / stable / decelerating",
  "market_maturity": "emerging / growing / mature / declining",
  "key_stats": [
    {{
      "label": "stat name",
      "value": "stat value with units",
      "source": "where this estimate comes from"
    }}
  ],
  "industry_trends": [
    {{
      "trend": "trend name",
      "impact": "how it affects this product",
      "direction": "positive / neutral / negative"
    }}
  ]
}}"""

REVENUE_PROMPT = """Generate revenue projections for this product. Use the design sheet data below.
Model three scenarios across a 3-year timeline. Be realistic — most startups don't turn profit in year 1.

Design Sheet:
{sheet_json}

Return a JSON object with this exact structure:
{{
  "pricing_model": "recommended pricing strategy (freemium, subscription, usage-based, etc.)",
  "pricing_tiers": [
    {{
      "name": "tier name",
      "price_monthly": 0,
      "features": ["included features"],
      "target_segment": "who this tier is for"
    }}
  ],
  "scenarios": {{
    "best_case": {{
      "year_1": {{ "revenue": 250000, "users": 5000, "paying_users": 800, "mrr": 20000 }},
      "year_2": {{ "revenue": 1200000, "users": 25000, "paying_users": 4000, "mrr": 100000 }},
      "year_3": {{ "revenue": 4000000, "users": 80000, "paying_users": 15000, "mrr": 330000 }},
      "assumptions": ["key assumptions for this scenario"]
    }},
    "likely_case": {{
      "year_1": {{ "revenue": 80000, "users": 2000, "paying_users": 300, "mrr": 6500 }},
      "year_2": {{ "revenue": 450000, "users": 10000, "paying_users": 1500, "mrr": 37000 }},
      "year_3": {{ "revenue": 1500000, "users": 35000, "paying_users": 6000, "mrr": 125000 }},
      "assumptions": ["key assumptions for this scenario"]
    }},
    "worst_case": {{
      "year_1": {{ "revenue": 15000, "users": 500, "paying_users": 50, "mrr": 1200 }},
      "year_2": {{ "revenue": 80000, "users": 2000, "paying_users": 300, "mrr": 6500 }},
      "year_3": {{ "revenue": 250000, "users": 8000, "paying_users": 1000, "mrr": 20000 }},
      "assumptions": ["key assumptions for this scenario"]
    }}
  }},
  "break_even_months": 18,
  "key_revenue_drivers": ["list of what drives revenue growth"],
  "revenue_risks": ["list of revenue risks"]
}}"""

MARKETING_PROMPT = """Generate a comprehensive marketing strategy for this product. Use the design sheet data below.
Focus on actionable, budget-conscious tactics suitable for a startup.

Design Sheet:
{sheet_json}

Return a JSON object with this exact structure:
{{
  "summary": "2-3 sentence marketing strategy overview",
  "channels": [
    {{
      "name": "Channel name (e.g. Content Marketing, Paid Ads, SEO)",
      "priority": "primary / secondary / experimental",
      "budget_monthly_usd": 500,
      "expected_cac": 25,
      "tactics": ["specific tactic 1", "specific tactic 2"],
      "timeline": "when to start this channel",
      "kpis": ["metric to track"]
    }}
  ],
  "launch_strategy": {{
    "pre_launch": ["action items before launch"],
    "launch_week": ["action items during launch"],
    "post_launch": ["action items after launch (30-90 days)"]
  }},
  "content_ideas": [
    {{
      "type": "blog / video / social / email / webinar",
      "title": "content piece title or theme",
      "goal": "what it achieves"
    }}
  ],
  "partnerships": [
    {{
      "type": "integration / affiliate / co-marketing / influencer",
      "description": "partnership opportunity"
    }}
  ],
  "budget_summary": {{
    "monthly_min_usd": 500,
    "monthly_max_usd": 5000,
    "allocation": [
      {{ "category": "Paid Ads", "pct": 40 }},
      {{ "category": "Content", "pct": 30 }},
      {{ "category": "Community", "pct": 20 }},
      {{ "category": "Tools & Software", "pct": 10 }}
    ]
  }}
}}"""


# ---------------------------------------------------------------------------
# Ordered sections for sequential generation
# ---------------------------------------------------------------------------
SECTIONS = [
    ("target_market", TARGET_MARKET_PROMPT),
    ("competitive_landscape", COMPETITIVE_PROMPT),
    ("market_metrics", METRICS_PROMPT),
    ("revenue_projections", REVENUE_PROMPT),
    ("marketing_strategies", MARKETING_PROMPT),
]

SECTION_LABELS = {
    "target_market": "Target Market Assessment",
    "competitive_landscape": "Competitive Analysis",
    "market_metrics": "Market Metrics & TAM/SAM/SOM",
    "revenue_projections": "Revenue Projections",
    "marketing_strategies": "Marketing Strategy",
}


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

async def get_analysis(db: AsyncSession, project_id: uuid.UUID) -> MarketAnalysis | None:
    """Fetch the market analysis for a project."""
    result = await db.execute(
        select(MarketAnalysis).where(MarketAnalysis.project_id == project_id)
    )
    return result.scalar_one_or_none()


async def get_design_sheet(db: AsyncSession, project_id: uuid.UUID) -> DesignSheet | None:
    """Fetch the design sheet for a project."""
    result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    return result.scalar_one_or_none()


def build_sheet_context(sheet: DesignSheet, project: Project) -> dict:
    """Build a context dictionary from the design sheet and project for prompt injection."""
    return {
        "project_name": project.name,
        "project_description": project.description or "",
        "platform": sheet.platform or project.platform or "custom",
        "problem": sheet.problem or "",
        "audience": sheet.audience or project.audience or "",
        "mvp": sheet.mvp or "",
        "features": sheet.features or [],
        "tone": sheet.tone or project.tone or "",
        "tech_constraints": sheet.tech_constraints or "",
        "success_metric": sheet.success_metric or "",
        "complexity": project.complexity or "medium",
    }


def build_context_from_artifact(artifact_ctx: dict) -> dict:
    """Build the same context dict shape from a unified artifact context (v2)."""
    return {
        "project_name": artifact_ctx.get("project_name", ""),
        "project_description": artifact_ctx.get("project_description", ""),
        "platform": artifact_ctx.get("platform") or "custom",
        "problem": artifact_ctx.get("discovery_summary") or artifact_ctx.get("problem") or "",
        "audience": artifact_ctx.get("audience") or "",
        "mvp": artifact_ctx.get("mvp") or "",
        "features": artifact_ctx.get("features") or [],
        "tone": artifact_ctx.get("tone") or "",
        "tech_constraints": artifact_ctx.get("tech_constraints") or "",
        "success_metric": artifact_ctx.get("success_metric") or "",
        "complexity": artifact_ctx.get("complexity") or "medium",
    }


async def _generate_section(sheet_json: str, prompt_template: str) -> dict:
    """Call Claude to generate one section of the analysis. Returns parsed JSON."""
    prompt = prompt_template.format(sheet_json=sheet_json)

    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        system=SECTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # Handle possible markdown code blocks
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


async def generate_market_analysis(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    force_regenerate: bool = False,
) -> AsyncGenerator[str, None]:
    """Generate a full market analysis, streaming progress via SSE events.

    Yields SSE-formatted strings: ``data: {json}\\n\\n``

    Event types:
    - section_start: {type, section, label}
    - section_token: {type, section, content}  (streaming tokens)
    - section_complete: {type, section, data}
    - complete: {type}
    - error: {type, message}
    """
    # Fetch project
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Project not found'})}\n\n"
        return

    # Fetch design sheet (may be None for v2 projects)
    sheet = await get_design_sheet(db, project_id)

    is_v2 = getattr(project, "flow_version", "v1") == "v2"

    if not sheet and not is_v2:
        yield f"data: {json.dumps({'type': 'error', 'message': 'No design sheet found. Complete Discovery first.'})}\n\n"
        return

    # Get or create analysis record
    analysis = await get_analysis(db, project_id)
    if analysis and not force_regenerate:
        if analysis.status == "complete":
            yield f"data: {json.dumps({'type': 'error', 'message': 'Analysis already exists. Use force_regenerate=true to regenerate.'})}\n\n"
            return

    if not analysis:
        analysis = MarketAnalysis(
            project_id=project_id,
            user_id=user_id,
            status="generating",
        )
        db.add(analysis)
        await db.flush()
    else:
        # Reset for regeneration
        analysis.status = "generating"
        analysis.error_message = None
        analysis.target_market = None
        analysis.competitive_landscape = None
        analysis.market_metrics = None
        analysis.revenue_projections = None
        analysis.marketing_strategies = None
        await db.flush()

    # Build context JSON — v2 uses artifact context, v1 uses design sheet
    if is_v2:
        from app.services.artifact_context_service import build_artifact_context
        artifact_ctx = await build_artifact_context(db, project_id, user_id)
        sheet_context = build_context_from_artifact(artifact_ctx)
    else:
        sheet_context = build_sheet_context(sheet, project)
    sheet_json = json.dumps(sheet_context, indent=2)

    # Generate each section sequentially, streaming progress
    total_sections = len(SECTIONS)
    for idx, (section_key, prompt_template) in enumerate(SECTIONS):
        label = SECTION_LABELS[section_key]
        yield f"data: {json.dumps({'type': 'section_start', 'section': section_key, 'label': label, 'progress': idx / total_sections})}\n\n"

        try:
            # Stream tokens for this section
            prompt = prompt_template.format(sheet_json=sheet_json)
            full_text = []

            async with client.messages.stream(
                model=settings.CLAUDE_MODEL,
                max_tokens=4096,
                system=SECTION_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for token in stream.text_stream:
                    full_text.append(token)
                    yield f"data: {json.dumps({'type': 'section_token', 'section': section_key, 'content': token})}\n\n"

            # Parse the completed section
            text = "".join(full_text).strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            section_data = json.loads(text)

            # Store in database
            setattr(analysis, section_key, section_data)
            await db.flush()

            yield f"data: {json.dumps({'type': 'section_complete', 'section': section_key, 'data': section_data, 'progress': (idx + 1) / total_sections})}\n\n"

        except json.JSONDecodeError as e:
            # If JSON parsing fails, store the raw text as a fallback
            fallback = {"raw": "".join(full_text).strip(), "parse_error": str(e)}
            setattr(analysis, section_key, fallback)
            await db.flush()
            yield f"data: {json.dumps({'type': 'section_complete', 'section': section_key, 'data': fallback, 'progress': (idx + 1) / total_sections})}\n\n"

        except Exception as e:
            analysis.status = "error"
            analysis.error_message = f"Failed generating {label}: {str(e)}"
            await db.flush()
            await db.commit()
            yield f"data: {json.dumps({'type': 'error', 'message': analysis.error_message})}\n\n"
            return

    # Mark complete
    analysis.status = "complete"
    await db.flush()
    await db.commit()

    yield f"data: {json.dumps({'type': 'complete', 'progress': 1.0})}\n\n"


async def generate_report(db: AsyncSession, project_id: uuid.UUID) -> dict | None:
    """Generate a formatted report dictionary from the stored analysis."""
    analysis = await get_analysis(db, project_id)
    if not analysis or analysis.status != "complete":
        return None

    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()

    return {
        "project_name": project.name if project else "Unknown",
        "generated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
        "sections": {
            "target_market": {
                "title": "Target Market Assessment",
                "data": analysis.target_market,
            },
            "competitive_landscape": {
                "title": "Competitive Analysis",
                "data": analysis.competitive_landscape,
            },
            "market_metrics": {
                "title": "Market Metrics & TAM/SAM/SOM",
                "data": analysis.market_metrics,
            },
            "revenue_projections": {
                "title": "Revenue Projections",
                "data": analysis.revenue_projections,
            },
            "marketing_strategies": {
                "title": "Marketing Strategy",
                "data": analysis.marketing_strategies,
            },
        },
    }
