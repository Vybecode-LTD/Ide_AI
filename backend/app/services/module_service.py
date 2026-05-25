"""
module_service.py — AI-guided module execution, question generation,
response extraction, and cross-module field pre-population.

Each module is a short AI-guided conversation (lite: 2-3 Qs, deep: 6-10 Qs).
The AI partner style carries over from the discovery session.
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

import anthropic

from app.core.config import settings
from app.services.modular_pathway_service import (
    get_module_definition,
    EXISTING_MODULE_IDS,
)
from app.services.partner_style_service import (
    get_partner_style_fragment,
    DEFAULT_PARTNER_STYLE,
)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_KEY)

# ── Cross-module field pre-population mappings ────────────────────────
# Source module -> list of (field_key, [target_module_ids])

CROSS_POPULATE_MAP: dict[str, list[dict]] = {
    "audience_persona_builder": [
        {
            "field": "audience_description",
            "targets": [
                "market_analysis", "launch_strategy",
                "marketing_messaging_framework", "pricing_strategy",
            ],
        },
    ],
    "problem_opportunity_framer": [
        {
            "field": "problem_statement",
            "targets": [
                "goals_success_metrics", "risk_assessment", "market_analysis",
            ],
        },
    ],
    "goals_success_metrics": [
        {
            "field": "success_metrics",
            "targets": [
                "sprint_planner", "financial_projection_builder",
                "investor_deck_outline",
            ],
        },
    ],
    "constraints_mapper": [
        {
            "field": "budget_range",
            "targets": [
                "budget_cost_estimator", "financial_projection_builder",
            ],
        },
    ],
    "brand_identity_framework": [
        {
            "field": "brand_voice_tone",
            "targets": [
                "creative_direction_brief", "content_strategy",
                "marketing_messaging_framework",
            ],
        },
    ],
    "risk_assessment": [
        {
            "field": "key_risks",
            "targets": [
                "assumptions_log", "regulatory_compliance_check",
                "investor_deck_outline",
            ],
        },
    ],
    "revenue_model_designer": [
        {
            "field": "revenue_model",
            "targets": [
                "financial_projection_builder", "business_model_canvas",
                "pricing_strategy",
            ],
        },
    ],
}


def _question_range(mode: str) -> tuple[int, int]:
    """Return (min, max) question count for a mode."""
    if mode == "deep":
        return (6, 10)
    return (2, 3)


def build_module_system_prompt(
    module_id: str,
    concept_sheet: dict,
    ai_partner_style: str = DEFAULT_PARTNER_STYLE,
    mode: str = "lite",
    pre_populated: dict | None = None,
) -> str:
    """
    Build the system prompt for a module conversation session.

    Layers:
    1. Module purpose and question guidance
    2. Partner style fragment (tone/behavior)
    3. Concept sheet context + pre-populated fields
    """
    defn = get_module_definition(module_id)
    if not defn:
        defn = {"label": module_id, "description": "Module session.", "group": "General"}

    min_q, max_q = _question_range(mode)

    parts = [
        f"You are guiding the user through the **{defn['label']}** module.",
        f"Purpose: {defn['description']}",
        f"\nMode: {'Deep' if mode == 'deep' else 'Lite'}",
        f"Ask between {min_q} and {max_q} focused questions, one at a time.",
        "Each question should build on the previous answer.",
        "Be conversational but efficient — don't repeat what the user already told you.",
    ]

    if mode == "deep":
        parts.append(
            "In Deep mode, explore nuances, edge cases, and extended detail. "
            "Ask follow-up questions when answers are vague or surface-level."
        )
    else:
        parts.append(
            "In Lite mode, cover only the essentials. Keep questions focused "
            "and don't over-explore unless the user volunteers extra detail."
        )

    # Concept sheet context
    sheet_summary = []
    for key in ["problem", "audience", "mvp", "tone", "platform", "tech_constraints", "success_metric"]:
        val = concept_sheet.get(key)
        if val:
            sheet_summary.append(f"- {key}: {val}")
    fields_data = concept_sheet.get("fields_data", {})
    for k, v in fields_data.items():
        sheet_summary.append(f"- {k}: {v}")

    if sheet_summary:
        parts.append("\n--- Project Context (from discovery) ---")
        parts.extend(sheet_summary)

    # Pre-populated fields from earlier modules
    if pre_populated:
        parts.append("\n--- Pre-populated from earlier modules (DO NOT re-ask) ---")
        for field_key, value in pre_populated.items():
            parts.append(f"- {field_key}: {value}")
        parts.append(
            "\nAcknowledge these known facts naturally. "
            "Do NOT ask the user to repeat information already provided above."
        )

    # Partner style fragment
    try:
        fragment = get_partner_style_fragment(ai_partner_style)
    except (KeyError, ValueError):
        fragment = get_partner_style_fragment(DEFAULT_PARTNER_STYLE)
    if fragment:
        parts.append(f"\n--- Partner Style ---\n{fragment}")

    # Output instructions
    parts.append(
        "\n--- Output Rules ---"
        "\nWhen you have asked all your questions, output a final message that:"
        "\n1. Summarises the key decisions made"
        "\n2. Ends with exactly this marker on its own line: [MODULE_COMPLETE]"
        "\n\nAfter each question, suggest 2-3 quick reply options on the LAST line as: "
        "[CHIPS: option1 | option2 | option3]"
    )

    return "\n".join(parts)


async def stream_module_response(
    messages: list[dict],
    system_prompt: str,
) -> AsyncGenerator[str, None]:
    """Stream a module conversation response token by token."""
    async with client.messages.stream(
        model=settings.CLAUDE_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def generate_first_question(
    module_id: str,
    concept_sheet: dict,
    ai_partner_style: str = DEFAULT_PARTNER_STYLE,
    mode: str = "lite",
    pre_populated: dict | None = None,
) -> str:
    """Generate the opening question for a module session (non-streaming)."""
    system_prompt = build_module_system_prompt(
        module_id, concept_sheet, ai_partner_style, mode, pre_populated,
    )

    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=512,
        system=system_prompt,
        messages=[{
            "role": "user",
            "content": "Let's begin this module. Ask me your first question.",
        }],
    )

    return response.content[0].text.strip()


async def extract_module_output(
    module_id: str,
    responses: list[dict],
) -> dict:
    """
    Extract structured output from a completed module conversation.

    Returns a dict of key fields extracted by AI from the Q&A transcript.
    """
    defn = get_module_definition(module_id)
    label = defn["label"] if defn else module_id

    # Build transcript
    transcript = []
    for msg in responses:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        transcript.append(f"{'AI' if role == 'assistant' else 'User'}: {content}")

    transcript_text = "\n".join(transcript)

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=512,
            system=(
                f"You are extracting structured output from the completed '{label}' module.\n"
                "Analyze the conversation transcript and extract the key decisions, "
                "data points, and conclusions.\n\n"
                "Return ONLY valid JSON with descriptive field names.\n"
                "Example: {\"target_audience\": \"...\", \"key_pain_points\": [...], \"decisions\": [...]}\n"
                "Keep field names consistent and snake_case."
            ),
            messages=[{
                "role": "user",
                "content": f"Extract structured output from this module conversation:\n\n{transcript_text[:3000]}",
            }],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception:
        return {"raw_transcript": transcript_text[:2000]}


def cross_populate_fields(
    completed_modules: dict[str, dict],
    target_module_id: str,
) -> dict:
    """
    Build pre-populated fields for a target module based on completed modules.

    Args:
        completed_modules: {module_id: extracted_output_dict}
        target_module_id: the module about to start

    Returns:
        Dict of field_key -> value to inject into the target module's context.
    """
    pre_populated: dict[str, str] = {}

    for source_id, mappings in CROSS_POPULATE_MAP.items():
        if source_id not in completed_modules:
            continue
        source_output = completed_modules[source_id]

        for mapping in mappings:
            if target_module_id not in mapping["targets"]:
                continue
            field_key = mapping["field"]
            # Look for the field in the source module's extracted output
            value = source_output.get(field_key)
            if not value:
                # Try fuzzy match — the extraction might use slightly different keys
                for k, v in source_output.items():
                    if field_key.replace("_", "") in k.replace("_", "").lower():
                        value = v
                        break
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(v) for v in value)
                pre_populated[field_key] = str(value)

    return pre_populated


async def generate_module_output(
    module_id: str,
    field_values: dict,
    project_name: str = "",
) -> dict:
    """
    Generate a rich formatted output for a has_output module.

    Uses the module's field values + label/description to produce a structured
    document (e.g. a Brand Identity Framework, Business Model Canvas, Investor
    Deck Outline). Returns a dict with 'title', 'content' (markdown string),
    and 'generated_at' (ISO timestamp).
    """
    import datetime

    defn = get_module_definition(module_id)
    if not defn:
        return {"error": "Module not found"}

    label = defn["label"]
    description = defn.get("description", "")
    fields = defn.get("fields") or []

    # Build a field summary for the prompt
    field_lines = []
    for f in fields:
        key = f.get("key", "")
        f_label = f.get("label", key)
        val = field_values.get(key)
        if val is not None:
            if isinstance(val, list):
                val_str = ", ".join(str(v) for v in val)
            elif isinstance(val, dict):
                val_str = "; ".join(f"{k}: {v}" for k, v in val.items())
            else:
                val_str = str(val)
            field_lines.append(f"- **{f_label}**: {val_str}")
        else:
            field_lines.append(f"- **{f_label}**: (not provided)")

    field_summary = "\n".join(field_lines)
    project_ctx = f" for the project '{project_name}'" if project_name else ""

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            system=(
                f"You are generating a polished '{label}' document{project_ctx}.\n"
                f"Module purpose: {description}\n\n"
                "Using the field values provided, produce a well-structured document in Markdown format.\n"
                "Be specific and actionable — this is a working document the user will export and reference.\n"
                "Use headers, bullet points, and bold text for readability.\n"
                "Do NOT include meta-commentary — just produce the document content.\n"
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Generate the {label} document based on these inputs:\n\n"
                    f"{field_summary}\n\n"
                    "Produce a complete, actionable document."
                ),
            }],
        )
        content = response.content[0].text.strip()
    except Exception:
        content = f"# {label}\n\n*Output generation failed. Please try again.*"

    return {
        "title": label,
        "content": content,
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


def is_module_complete(response_text: str) -> bool:
    """Check if the AI has signalled module completion."""
    return "[MODULE_COMPLETE]" in response_text


def is_existing_module(module_id: str) -> bool:
    """Check if a module_id maps to an existing page (not an AI conversation)."""
    return module_id in EXISTING_MODULE_IDS


def count_questions_asked(messages: list[dict]) -> int:
    """Count how many questions the AI has asked (assistant messages)."""
    return sum(1 for m in messages if m.get("role") == "assistant")
