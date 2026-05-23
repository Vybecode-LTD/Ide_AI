"""
ai_service.py — Claude API wrapper and prompt builder.
All AI calls go through this service for centralized prompt management.
"""
from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, AsyncGenerator

import anthropic

from app.core.config import settings

if TYPE_CHECKING:
    from app.pathways.base import PathwayConfig

logger = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_KEY)



def _get_pathway(pathway: PathwayConfig | None = None) -> PathwayConfig:
    """Resolve a pathway, falling back to software_product."""
    if pathway is not None:
        return pathway
    from app.pathways import PathwayRegistry
    return PathwayRegistry.get("software_product")


# ---------------------------------------------------------------------------
# Software-product-specific platform prerequisites (used when pathway has
# platform-based context injection).  Kept here because it's consumed by
# build_system_prompt for the software pathway.
# ---------------------------------------------------------------------------
PLATFORM_PREREQUISITES: dict[str, dict] = {
    "mobile": {
        "summary": "Mobile app (iOS / Android)",
        "languages": "Swift or Kotlin (native), Dart (Flutter), JavaScript/TypeScript (React Native / Expo)",
        "sdks": "Xcode + iOS SDK, Android Studio + Android SDK, Flutter SDK, Expo / React Native CLI",
        "build": "Requires compilation. iOS requires macOS + Xcode. Android uses Gradle.",
        "distribution": "Apple App Store / Google Play Store. Needs signing certificates and store accounts.",
        "notes": "Cross-platform (Flutter, RN) reduces effort but may limit native API access. Push notifications require platform-specific setup (APNs, FCM).",
    },
    "web": {
        "summary": "Full-stack web application",
        "languages": "JavaScript/TypeScript (frontend), Python / Node.js / Go (backend)",
        "sdks": "React / Vue / Svelte (frontend), Express / FastAPI / Next.js (full-stack)",
        "build": "Frontend bundled with Vite or Webpack. Backend runs as server process. No compilation for interpreted stacks.",
        "distribution": "Deploy to Vercel, Railway, AWS, etc. Accessible via browser — no install.",
        "notes": "Lowest friction to ship. Consider SSR/SSG for SEO. PWA for offline.",
    },
    "desktop": {
        "summary": "Native desktop application (Windows / Mac / Linux)",
        "languages": "C++ or C# (native), JavaScript/TypeScript (Electron), Rust + JS (Tauri), Swift (macOS)",
        "sdks": "Electron, Tauri, .NET MAUI, Qt (C++), SwiftUI (macOS only)",
        "build": "REQUIRES COMPILATION for native builds. Electron/Tauri bundle web tech into desktop binaries.",
        "distribution": "Direct download, Microsoft Store, Mac App Store. Code signing required for trusted installs.",
        "notes": "Electron is quickest but heavy (~150 MB). Tauri is lighter (~5 MB) but uses Rust. Native C++/C# gives best performance but longest dev time.",
    },
    "browser-extension": {
        "summary": "Browser extension (Chrome / Firefox / Edge)",
        "languages": "JavaScript / TypeScript",
        "sdks": "Chrome Extensions API (Manifest V3), WebExtensions API (Firefox cross-compat)",
        "build": "Bundled with Webpack or Vite. No compilation. Manifest V3 required for Chrome.",
        "distribution": "Chrome Web Store, Firefox Add-ons, Edge Add-ons. Review process required.",
        "notes": "Limited to browser context. Service workers replace background pages in MV3. Content scripts run in page context.",
    },
    "vst/vsti-plug-in": {
        "summary": "Audio DSP plug-in loaded inside a DAW (Digital Audio Workstation)",
        "languages": "C++ (industry standard via JUCE framework), Rust (emerging via nih-plug), Python bridge (experimental — user has a custom toolchain in progress)",
        "sdks": "JUCE 8 (C++ — most widely used), iPlug2 (C++), nih-plug (Rust), DPF (DISTRHO Plugin Framework)",
        "build": "REQUIRES C++ COMPILATION via CMake or Projucer. Outputs VST3, AU, AAX, and CLAP binaries. Must be compiled per-platform (Win/Mac/Linux).",
        "distribution": "Direct download from developer website, or marketplaces (Plugin Boutique, KVR). No app store — users install to DAW plug-in folder.",
        "notes": "Strict real-time audio constraints: NO memory allocation, NO blocking calls in processBlock(). DSP knowledge required (filters, oscillators, FFT). Audio buffer sizes 64–2048 samples. Must support multiple sample rates (44.1k, 48k, 96k). UI is typically custom-drawn, not native OS widgets. The user is building a Python-to-VST bridge — keep this in mind for pipeline suggestions.",
    },
    "bubble": {
        "summary": "Bubble no-code web app",
        "languages": "No-code (visual programming in Bubble editor)",
        "sdks": "Bubble visual editor, Bubble API Connector for external integrations",
        "build": "No compilation. Apps built entirely in the visual editor.",
        "distribution": "Hosted on Bubble infrastructure. Custom domains available.",
        "notes": "Great for MVPs. Limited by Bubble's constraints for complex custom logic. Responsive design requires manual breakpoint configuration.",
    },
    "webflow": {
        "summary": "Webflow visual web design and CMS",
        "languages": "No-code (visual design). Optional custom code embeds (HTML/CSS/JS).",
        "sdks": "Webflow Designer, Webflow CMS, Webflow Logic (automation)",
        "build": "No compilation. Visual design published directly.",
        "distribution": "Hosted on Webflow or exported as static HTML.",
        "notes": "Best for marketing sites and content-driven apps. CMS is built-in. E-commerce available. Complex dynamic apps may outgrow Webflow.",
    },
    "flutterflow": {
        "summary": "FlutterFlow visual app builder (generates Flutter/Dart)",
        "languages": "Visual builder generates Dart / Flutter code. Custom functions in Dart.",
        "sdks": "FlutterFlow editor, Flutter SDK (for code export), Firebase (default backend)",
        "build": "Visual builder compiles to Flutter. Code can be exported and compiled locally.",
        "distribution": "Web deploy from FlutterFlow. App Store / Play Store via Flutter build.",
        "notes": "Generates real Flutter code that can be exported. Firebase deeply integrated. Supabase also supported.",
    },
    "bolt": {
        "summary": "Bolt AI-powered full-stack app builder",
        "languages": "JavaScript / TypeScript (generated by AI)",
        "sdks": "React (frontend), Node.js (backend) — AI picks stack based on prompt",
        "build": "AI generates and deploys code. No manual compilation needed.",
        "distribution": "Deployed directly from Bolt. Exportable source code.",
        "notes": "AI generates the full app from a prompt. Best for rapid prototyping. May need manual refinement for production.",
    },
    "lovable": {
        "summary": "Lovable AI app builder (formerly GPT Engineer)",
        "languages": "TypeScript / React (AI-generated)",
        "sdks": "React + Vite (frontend), Supabase (backend/database)",
        "build": "AI generates complete app. Supabase handles backend automatically.",
        "distribution": "Deployed to Lovable hosting or exported as source.",
        "notes": "AI-first development. Supabase deeply integrated for auth, database, storage. Good for MVPs and internal tools.",
    },
    "claude-code": {
        "summary": "Claude Code AI-assisted development",
        "languages": "Any — Claude Code supports all major languages",
        "sdks": "Whatever the project requires — Claude Code assists with any stack",
        "build": "Depends on chosen tech stack. Claude Code helps write and debug.",
        "distribution": "Depends on chosen deployment target.",
        "notes": "AI-assisted coding tool. The user writes code with Claude's help. No platform constraints — suggest the best stack for the user's needs.",
    },
    "cursor": {
        "summary": "Cursor AI-powered code editor",
        "languages": "Any — Cursor supports all major languages",
        "sdks": "Whatever the project requires — Cursor assists with any stack",
        "build": "Depends on chosen tech stack.",
        "distribution": "Depends on chosen deployment target.",
        "notes": "AI-assisted IDE. The user writes code with AI help. Recommend the best stack for their specific product needs.",
    },
    "replit": {
        "summary": "Replit cloud development and hosting",
        "languages": "Python, JavaScript/TypeScript, Go, Rust, and many more",
        "sdks": "Any — Replit supports most package managers (pip, npm, cargo, etc.)",
        "build": "Cloud-based. No local setup needed. Auto-builds on run.",
        "distribution": "Hosted on Replit. Custom domains available. Deployments included.",
        "notes": "Great for collaboration and fast prototyping. Cloud-only — no local dev environment needed. Database (PostgreSQL) and secrets management built-in.",
    },
    "n8n": {
        "summary": "n8n workflow automation platform",
        "languages": "JavaScript / TypeScript (for custom nodes). No-code for built-in nodes.",
        "sdks": "n8n SDK for custom node development",
        "build": "No compilation for standard workflows. Custom nodes require npm packaging.",
        "distribution": "Self-hosted (Docker) or n8n Cloud.",
        "notes": "Visual workflow builder for automation and integrations. 400+ built-in integrations. Custom nodes extend functionality. Webhook triggers available.",
    },
    "custom": {
        "summary": "Custom or unspecified platform",
        "languages": "Depends on the user's target",
        "sdks": "Depends on the user's target",
        "build": "Varies by platform.",
        "distribution": "Varies by platform.",
        "notes": "Ask the user to clarify their target platform so you can give specific guidance on language, SDK, build, and distribution requirements.",
    },
}


def _get_stage_prompt(pathway: PathwayConfig, stage: str) -> str:
    """Look up the system_prompt for a stage within the pathway's stages list."""
    for s in pathway.stages:
        if s.id == stage:
            return s.system_prompt
    # Fallback: first stage
    return pathway.stages[0].system_prompt if pathway.stages else ""


def _build_platform_block(platform: str) -> str | None:
    """Build platform-specific context block for software pathway."""
    prereqs = PLATFORM_PREREQUISITES.get(platform, PLATFORM_PREREQUISITES.get("custom", {}))
    if not prereqs:
        return f"\nThe user is targeting the {platform} platform. Keep recommendations relevant to this platform's capabilities and constraints."
    block = [f"\n## TARGET PLATFORM: {prereqs.get('summary', platform)}"]
    if prereqs.get("languages"):
        block.append(f"Languages: {prereqs['languages']}")
    if prereqs.get("sdks"):
        block.append(f"SDKs/Frameworks: {prereqs['sdks']}")
    if prereqs.get("build"):
        block.append(f"Build: {prereqs['build']}")
    if prereqs.get("distribution"):
        block.append(f"Distribution: {prereqs['distribution']}")
    if prereqs.get("notes"):
        block.append(f"Notes: {prereqs['notes']}")
    block.append("Keep ALL recommendations aligned with these platform requirements. If the user's idea conflicts with platform constraints, flag it proactively.")
    return "\n".join(block)


def strip_chips_line(text: str) -> str:
    """Remove the [CHIPS: ...] line from AI response text."""
    return re.sub(r'\n?\[CHIPS:.*?\]', '', text).strip()


async def build_system_prompt(
    platform: str,
    stage: str,
    sheet_context: dict | None = None,
    user_name: str | None = None,
    memories: str | None = None,
    *,
    pathway: PathwayConfig | None = None,
    ai_partner_style: str | None = None,
    message_count: int = 0,
) -> str:
    """Build a 3-layer system prompt: base + partner fragment + session context.

    Layer 1 — Base discovery prompt:
        App role, safety, extraction, stage logic, formatting.
    Layer 2 — Partner style fragment:
        Behaviour, tone, questioning style, guardrails.
    Layer 3 — Session context:
        Platform, stage, known fields, user info, memories.

    Args:
        platform: Target platform string (e.g. 'bubble', 'custom').
        stage: Current discovery stage name.
        sheet_context: Partial design sheet dict for context injection.
        user_name: If provided, address the user by name in the greeting.
        memories: Formatted memory context block from memory_service.format_memory_context().
        pathway: PathwayConfig to use. Falls back to software_product if None.
        ai_partner_style: Partner collaboration style (e.g. 'skeptic', 'coach').
        message_count: Number of messages in the conversation so far (for pacing).
    """
    from app.services.partner_style_service import get_partner_style_fragment, DEFAULT_PARTNER_STYLE

    pw = _get_pathway(pathway)

    # ── Layer 1: Base discovery persona ──
    parts = [pw.base_persona]

    # ── Layer 2: Partner style fragment ──
    style = ai_partner_style or DEFAULT_PARTNER_STYLE
    partner_fragment = get_partner_style_fragment(style)
    parts.append(f"\n{partner_fragment}")

    # ── Layer 3: Session context ──
    if user_name:
        parts.append(f"\nThe user's name is {user_name}. Address them by name where natural — especially in greetings.")

    if memories:
        parts.append(f"\n{memories}")

    # Platform context injection (software pathway only — has PLATFORM_PREREQUISITES)
    if platform and pw.id == "software_product":
        platform_block = _build_platform_block(platform)
        if platform_block:
            parts.append(platform_block)

    stage_prompt = _get_stage_prompt(pw, stage)
    parts.append(f"\n{stage_prompt}")

    if sheet_context:
        filled = {k: v for k, v in sheet_context.items() if v}
        if filled:
            parts.append(f"\nDesign sheet so far: {json.dumps(filled, indent=2)}")
            parts.append(
                "These fields are ALREADY ANSWERED. Do NOT ask about them again. "
                "Build on them, go deeper on unexplored angles, or move to the next topic."
            )

    # ── Anti-repetition & Progression Rules ──
    parts.append(f"""
CONVERSATION RULES (CRITICAL — violation makes you useless):

Turn count: {message_count} messages so far.

1. NEVER REPEAT YOURSELF. Read the conversation history. If you already asked something
   or made a point, DO NOT say it again in any form. No rephrasing the same question.
   No circling back. Each response must cover NEW GROUND.

2. PROGRESS RELENTLESSLY. Every response must move the conversation forward:
   - If you asked about X and got an answer, acknowledge it briefly and pivot to Y
   - If the user gave a short answer, dig deeper on THAT answer (don't restart the topic)
   - If you've covered 2+ questions in this stage, start wrapping up and transitioning

3. VARY YOUR APPROACH. Never open two responses the same way. Mix up your patterns:
   - Sometimes lead with an insight about what they just said
   - Sometimes challenge an assumption
   - Sometimes offer a concrete suggestion then ask for reaction
   - Sometimes share a relevant analogy or comparison
   - NEVER start consecutive responses with "Great!" or "That's interesting!"

4. STAY CONCISE. 2-4 sentences max per response (excluding chips). You're a rapid-fire
   collaborator, not a lecturer. If your response is getting long, you're over-explaining.

5. ONE QUESTION PER TURN. Ask exactly ONE focused question. Never stack multiple questions.
   The question should be impossible to answer with a single word — force specificity.""")

    parts.append("""
QUICK REPLY CHIPS (MANDATORY — never skip this):
When you ask a question, embed 2-3 specific answer options that directly answer YOUR question.
Place them on the very last line in this exact format: [CHIPS: answer1 | answer2 | answer3]

Rules for good chips:
- Each chip must be a DIRECT, COMPLETE answer to the question you just asked
- If you ask "Who is this for?" → [CHIPS: Small business owners | College students | Enterprise teams]
- If you ask "What's the core problem?" → [CHIPS: People waste hours on manual data entry | Teams can't collaborate in real-time | No affordable option exists]
- NEVER use vague chips like "Tell me more" or "Let's move on" — those are useless
- Chips should be 3-10 words each — short enough to tap, specific enough to be a real answer
- The [CHIPS: ...] line is hidden from the user and shown as clickable buttons. Do NOT include it in your visible message.""")

    return "\n".join(parts)


async def build_greeting_prompt(
    project_description: str | None = None,
    platform: str = "custom",
    *,
    pathway: PathwayConfig | None = None,
    ai_partner_style: str | None = None,
) -> str:
    """Build a system prompt specifically for the initial AI greeting."""
    from app.services.partner_style_service import get_partner_style_fragment, DEFAULT_PARTNER_STYLE

    pw = _get_pathway(pathway)
    parts = [pw.base_persona]

    # Partner style fragment
    style = ai_partner_style or DEFAULT_PARTNER_STYLE
    parts.append(f"\n{get_partner_style_fragment(style)}")

    # Platform context (software pathway only)
    if platform and pw.id == "software_product":
        prereqs = PLATFORM_PREREQUISITES.get(platform, PLATFORM_PREREQUISITES.get("custom", {}))
        if prereqs and prereqs.get("summary"):
            parts.append(f"\nTarget platform: {prereqs['summary']}. Languages: {prereqs.get('languages', 'TBD')}. Build: {prereqs.get('build', 'TBD')}.")
        elif platform != "custom":
            parts.append(f"\nThe user is targeting the {platform} platform.")

    greeting_prompt = _get_stage_prompt(pw, "greeting")
    parts.append(f"\n{greeting_prompt}")

    if project_description:
        parts.append(f"\nThe user described their project idea as: \"{project_description}\"")
        parts.append("Reference their idea with enthusiasm and ask a focused follow-up question.")
    else:
        parts.append("\nNo project description was provided yet. Ask them to describe what they want to build.")

    parts.append("""
QUICK REPLY CHIPS (MANDATORY — never skip this):
End your response with 2-3 specific answer options on the very last line.
Format: [CHIPS: answer1 | answer2 | answer3]
Each chip must directly answer the question you asked. Never use vague options like "Tell me more".
Example: If you ask "What kind of product?" → [CHIPS: A marketplace connecting buyers and sellers | A productivity tool for remote teams | A social platform for hobbyists]""")

    return "\n".join(parts)


async def build_unified_discovery_prompt(
    *,
    project_name: str,
    project_description: str | None,
    primary_category: str | None,
    platform: str | None,
    modules: list[dict],
    current_fields: dict[str, dict],
    ai_partner_style: str | None = None,
    user_name: str | None = None,
    memories: str | None = None,
    message_count: int = 0,
) -> str:
    """Build the unified-discovery system prompt for the v2 flow.

    Tells the AI about every assembled module + its field schema + what's
    already filled, and instructs it to funnel toward filling the most
    important unfilled REQUIRED field next.

    Args:
        project_name, project_description, primary_category, platform — project context
        modules — assembled module list with embedded `fields` schemas
        current_fields — dict module_id → {field_key: value} of what's already filled
        ai_partner_style — partner persona to layer on top
        user_name, memories — optional personalization
        message_count — total turns so far (for pacing)
    """
    from app.services.partner_style_service import get_partner_style_fragment, DEFAULT_PARTNER_STYLE

    parts = [
        "You are a discovery partner helping the user build a COMPLETE design kit "
        "for their project. The kit is a structured set of modules. Your job over "
        "the next several turns is to gather enough information to fill in every "
        "REQUIRED field across the modules. After the required fields are filled, "
        "you may optionally gather optional fields if the user is engaged."
    ]

    # ── Project header ──
    parts.append(f"""
PROJECT
- Name: {project_name}
- Description: {project_description or '(none yet — ask the user to clarify if needed)'}
- Category: {primary_category or 'general'}
- Platform: {platform or 'custom'}""")

    # ── Partner style fragment ──
    style = ai_partner_style or DEFAULT_PARTNER_STYLE
    parts.append(f"\n{get_partner_style_fragment(style)}")

    if user_name:
        parts.append(f"\nThe user's name is {user_name}. Address them by name where natural.")
    if memories:
        parts.append(f"\n{memories}")

    # ── Module schemas + filled state ──
    n_modules = len(modules)
    parts.append(f"\nMODULES IN THIS DESIGN KIT ({n_modules})")

    for i, mod in enumerate(modules, 1):
        mid = mod.get("module_id") or mod.get("id") or "unknown"
        label = mod.get("label", mid)
        fields = mod.get("fields") or []
        filled_for_module = current_fields.get(mid, {})

        parts.append(f"\n{i}. {label} [{mid}]")
        if not fields:
            parts.append("   (no detailed field schema — gather general info, then move on)")
            continue
        for f in fields:
            fk = f.get("key", "")
            req = "REQUIRED" if f.get("required") else "optional"
            ftype = f.get("type", "text")
            hint = f.get("extraction_hint", "")
            if fk in filled_for_module:
                parts.append(f"   - {fk} ({req} {ftype}) — STATUS: filled. (hint: {hint})")
            else:
                parts.append(f"   - {fk} ({req} {ftype}) — STATUS: missing. {hint}")

    # ── Discovery rules ──
    parts.append(f"""

DISCOVERY RULES (CRITICAL — violation makes you useless)
Turn count so far: {message_count}

1. ONE QUESTION PER TURN. Look at the MODULES list above. Find the FIRST REQUIRED
   field marked "STATUS: missing" (top-to-bottom). Ask a focused, specific question
   that elicits a direct answer for that field. Never stack multiple questions.

2. NEVER REPEAT YOURSELF. If you already asked something or made a point, don't
   say it again in any form. Each response must cover NEW GROUND.

3. SHORT RESPONSES. 2-4 sentences max (excluding the chips line). Rapid-fire
   collaboration, not lectures.

4. PROGRESS RELENTLESSLY. Every turn must fill at least one missing field. If the
   user's answer was vague, dig deeper on THAT answer (don't restart the topic).

5. AFTER REQUIRED FIELDS ARE FILLED, you may gather optional fields. Make it clear
   the user can hit "Proceed to Design Kit" whenever they want — you're not gating.

6. RESPECT WHAT'S FILLED. Build on filled values to ask better questions about
   adjacent missing fields. Don't ask the user to repeat information you can see.

7. VARY YOUR APPROACH. Sometimes lead with an insight about what they said,
   sometimes challenge an assumption, sometimes offer a concrete suggestion.
   Never two consecutive responses opening with "Great!" or "That's interesting!".""")

    parts.append("""
QUICK REPLY CHIPS (MANDATORY — never skip)
End every response with 2-3 specific answer options on the very last line.
Format: [CHIPS: answer1 | answer2 | answer3]

Each chip must be a DIRECT, COMPLETE answer to the question you just asked.
- 3-10 words per chip
- Specific and tappable (e.g. "Solo founder, no team" not "Tell me more")
- The [CHIPS: ...] line is stripped from the displayed message and rendered as buttons.""")

    return "\n".join(parts)


async def extract_module_fields(
    messages: list,
    modules: list[dict],
    current_fields: dict[str, dict],
) -> dict:
    """Extract NEW per-module field values from the conversation using Claude.

    Returns a dict mapping ``"module_id.field_key"`` to the extracted value.
    Lists become JSON arrays; dicts become JSON objects; text/longtext become
    strings. Empty dict if extraction fails or finds nothing new.
    """
    if not modules:
        return {}

    schema_lines: list[str] = []
    filled_lines: list[str] = []
    for mod in modules:
        mid = mod.get("module_id") or mod.get("id")
        if not mid:
            continue
        for f in mod.get("fields") or []:
            fk = f.get("key", "")
            ftype = f.get("type", "text")
            req = "required" if f.get("required") else "optional"
            hint = f.get("extraction_hint", "")
            schema_lines.append(f"- {mid}.{fk} ({ftype}, {req}): {hint}")
        filled_for_module = current_fields.get(mid, {})
        for fk, val in filled_for_module.items():
            preview = str(val)[:120]
            filled_lines.append(f"- {mid}.{fk} = {preview}")

    extraction_prompt = f"""Extract NEW factual information from the conversation that matches these field schemas.
Return ONLY a JSON object mapping "module_id.field_key" to the extracted value.

Field schemas (the only valid keys you may return):
{chr(10).join(schema_lines)}

Already filled (do NOT repeat unless the user explicitly updated them in the latest messages):
{chr(10).join(filled_lines) if filled_lines else '(nothing filled yet)'}

Rules:
- For "list" fields, return a JSON array of strings
- For "dict" fields, return a JSON object
- For "text" / "longtext" fields, return a JSON string
- ONLY include fields where you have NEW information from the latest user messages
- If unsure, OMIT the field entirely (do not return null or empty strings)
- Return strictly JSON. No commentary, no markdown.

Example return shape:
{{
  "audience_persona_builder.primary_persona": "Early-stage SaaS founders aged 28-45",
  "audience_persona_builder.pain_points": ["Time poverty", "Funding pressure"],
  "problem_opportunity_framer.urgency": "AI tooling just became affordable"
}}"""

    extraction_messages = list(messages) + [{"role": "user", "content": extraction_prompt}]

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2048,
            system="You are a data extraction assistant. Return only valid JSON, no commentary.",
            messages=extraction_messages,
        )
    except Exception as exc:
        logger.warning("Module field extraction API call failed: %s", exc)
        return {}

    try:
        text = response.content[0].text.strip()
    except (IndexError, AttributeError):
        return {}

    # Strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    # Find the first JSON object in the response
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        logger.warning("Module field extraction returned no JSON: %r", text[:200])
        return {}

    try:
        extracted = json.loads(json_match.group(0))
    except json.JSONDecodeError as exc:
        logger.warning("Module field extraction JSON parse failed: %s", exc)
        return {}

    if not isinstance(extracted, dict):
        return {}

    # Validate keys against schema — drop anything unrecognized
    valid_keys: set[str] = set()
    for mod in modules:
        mid = mod.get("module_id") or mod.get("id")
        if not mid:
            continue
        for f in mod.get("fields") or []:
            fk = f.get("key", "")
            if fk:
                valid_keys.add(f"{mid}.{fk}")

    return {k: v for k, v in extracted.items() if k in valid_keys and v not in (None, "", [], {})}


async def stream_response(messages: list, system_prompt: str) -> AsyncGenerator[str, None]:
    """Stream Claude API response tokens as an async generator."""
    async with client.messages.stream(
        model=settings.CLAUDE_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def extract_sheet_fields(
    messages: list,
    *,
    pathway: PathwayConfig | None = None,
) -> dict:
    """Extract design sheet fields from conversation using Claude.

    Uses the pathway's extraction_prompt to know which fields to look for.
    """
    pw = _get_pathway(pathway)
    extraction_messages = messages + [
        {"role": "user", "content": pw.extraction_prompt}
    ]

    try:
        response = await client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            system="You are a data extraction assistant. Return only valid JSON, no explanatory text.",
            messages=extraction_messages,
        )
    except Exception as exc:
        logger.warning("Sheet extraction API call failed: %s", exc)
        return {}

    try:
        text = response.content[0].text.strip()
    except (IndexError, AttributeError):
        logger.warning("Sheet extraction returned empty response")
        return {}

    # Try to extract JSON from the response, handling various Claude formats:
    # 1. Pure JSON: {"key": "value"}
    # 2. Markdown fenced: ```json\n{...}\n```
    # 3. Text before/after JSON: "Here's the data:\n{...}"
    parsed = _parse_json_from_text(text)
    if parsed is None:
        logger.warning("Sheet extraction returned unparseable text: %.200s", text)
        return {}

    if not parsed:
        logger.debug("Sheet extraction returned empty object (too early in conversation)")
    else:
        logger.info("Sheet extraction found fields: %s", list(parsed.keys()))

    return parsed


def _parse_json_from_text(text: str) -> dict | None:
    """Attempt to parse a JSON object from text that may contain markdown or prose.

    Returns the parsed dict, or None if no valid JSON object could be found.
    """
    # Strategy 1: Try direct parse (pure JSON response)
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown fenced code block
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if fence_match:
        try:
            result = json.loads(fence_match.group(1).strip())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find the first { ... } block in the text
    brace_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    return None


async def generate_quick_chips(ai_response: str, stage: str = "greeting") -> list[str]:
    """Parse quick reply chips from AI response text.

    Strategy:
    1. Look for explicit [CHIPS: a | b | c] tag anywhere in the text (preferred)
    2. Fallback: extract options from the AI's own question (e.g. "X, Y, or Z?")
    3. Last resort: generate answer-starters based on the question
    """
    import re

    # ── Strategy 1: Parse explicit [CHIPS:] tag ──
    # Search anywhere in the text (not just line-start) and case-insensitive
    chips_match = re.search(r'\[chips:\s*(.+?)\]', ai_response, re.IGNORECASE)
    if chips_match:
        inner = chips_match.group(1)
        chips = [c.strip().strip('"').strip("'") for c in inner.split("|") if c.strip()]
        if chips:
            return chips

    # ── Strategy 2: Extract options from "X, Y, or Z?" patterns ──
    # Find the last question in the response
    sentences = re.split(r'(?<=[.!?])\s+', ai_response.strip())
    questions = [s for s in sentences if '?' in s]
    if questions:
        last_q = questions[-1]
        # Match "A, B, or C" pattern (with or without Oxford comma)
        or_match = re.search(r'([\w\s\-\']+),\s+([\w\s\-\']+),?\s+or\s+([\w\s\-\']+)', last_q)
        if or_match:
            chips = [g.strip().capitalize() for g in or_match.groups() if g.strip()]
            if chips and all(len(c) < 60 for c in chips):
                return chips

    # ── Strategy 3: Generate answer-starters from the question ──
    if questions:
        last_q = questions[-1].strip().rstrip('?').lower()
        if any(w in last_q for w in ['who', 'audience', 'user', 'customer', 'target', 'people', 'demographic']):
            return ["Individual consumers", "Small businesses", "Enterprise teams"]
        if any(w in last_q for w in ['what problem', 'pain point', 'challenge', 'struggle', 'frustrat', 'difficult']):
            return ["It's too slow and manual", "Existing tools are too expensive", "Nothing good exists yet"]
        if any(w in last_q for w in ['how', 'currently', 'today', 'right now', 'existing', 'already']):
            return ["Spreadsheets and manual work", "Cobbled-together free tools", "Expensive enterprise software"]
        if any(w in last_q for w in ['feature', 'must-have', 'capability', 'function', 'need', 'essential']):
            return ["Real-time collaboration", "Automated workflows", "Analytics and reporting"]
        if any(w in last_q for w in ['budget', 'cost', 'spend', 'price', 'invest', 'afford']):
            return ["Under $100/month", "$100-500/month", "Whatever it takes to do it right"]
        if any(w in last_q for w in ['timeline', 'launch', 'deadline', 'when', 'soon', 'time frame', 'hurry']):
            return ["Within 1-2 months", "3-6 months", "No rush — quality first"]
        if any(w in last_q for w in ['platform', 'device', 'where', 'deploy', 'host', 'run']):
            return ["Web app (browser)", "Mobile app (iOS/Android)", "Desktop application"]
        if any(w in last_q for w in ['tone', 'feel', 'vibe', 'style', 'brand', 'look']):
            return ["Professional and polished", "Casual and friendly", "Minimal and clean"]
        if any(w in last_q for w in ['revenue', 'monetiz', 'money', 'business model', 'charge', 'pay']):
            return ["Subscription (monthly/yearly)", "One-time purchase", "Freemium with upgrades"]
        if any(w in last_q for w in ['different', 'unique', 'stand out', 'competitor', 'advantage', 'better']):
            return ["Simpler UX than competitors", "Lower price point", "Unique feature no one else has"]
        if any(w in last_q for w in ['scale', 'grow', 'big', 'expand', 'future']):
            return ["Start small, grow organically", "Aim for rapid growth", "Build for enterprise scale from day one"]
        if any(w in last_q for w in ['important', 'priorit', 'focus', 'first', 'main', 'core']):
            return ["Speed and simplicity", "Comprehensive feature set", "Beautiful design and UX"]
        # Generic but contextual answer-starters
        return ["Yes, exactly", "Not quite — here's what I mean...", "I'm still figuring that out"]

    return ["Yes, exactly", "Not quite — let me explain", "I have a different angle"]
