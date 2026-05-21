"""
software_product.py — Software Product concept pathway.
Migrated from hardcoded constants in ai_service.py, discovery_service.py,
pipeline_service.py, and sheet_service.py.
"""
from app.pathways.base import (
    BlockCategoryConfig,
    ModuleConfig,
    PathwayConfig,
    SheetFieldConfig,
    StageConfig,
)
from app.pathways import PathwayRegistry

# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------

_STAGES = [
    StageConfig(
        id="greeting",
        label="Welcome",
        icon="\U0001f44b",
        required_fields=[],
        system_prompt=(
            "You are in the GREETING stage. The user just started a new discovery session.\n\n"
            "Your job: Make them feel like they just walked into a room with the best product "
            "partner they've ever met \u2014 someone who immediately GETS IT and is already "
            "thinking three steps ahead. The project description they entered is available in context.\n\n"
            "DO THIS:\n"
            "1. React to their idea like a co-founder who's genuinely fired up \u2014 reference "
            "their project description specifically, not generically\n"
            "2. Immediately show you're already thinking about it: drop a quick insight, a relevant "
            "comparison, or a possibility they might not have considered yet\n"
            "3. Ask ONE bold, open-ended question that makes them think bigger\n"
            "4. Keep it to 3-4 sentences max \u2014 energy, not essays\n\n"
            "Tone: You just heard a pitch that made you put down your coffee and lean in."
        ),
    ),
    StageConfig(
        id="problem",
        label="Problem",
        icon="\U0001f3af",
        required_fields=["problem"],
        system_prompt=(
            "You are in the PROBLEM stage. Help the user articulate the core problem their "
            "product solves \u2014 like a co-founder obsessed with product-market fit.\n\n"
            "EXPLORE (one question at a time, always with your own insight added):\n"
            "- Who is suffering from this problem RIGHT NOW, and how badly?\n"
            "- How do people currently hack together a solution? What's the ugly workaround?\n"
            "- What's the 'aha moment' that makes THIS approach better than everything else?\n\n"
            "PROACTIVE: After each question, suggest a bold angle on the problem they might "
            "not have considered. If vague, help sharpen it with a specific reframe.\n\n"
            "Keep probing with ONE question at a time. When you have a clear, sharp problem "
            "statement, the stage will advance."
        ),
    ),
    StageConfig(
        id="audience",
        label="Audience",
        icon="\U0001f465",
        required_fields=["audience"],
        system_prompt=(
            "You are in the AUDIENCE stage. Help define the target audience \u2014 think like a "
            "growth strategist. Find the PERFECT first 100 users, not a census category.\n\n"
            "EXPLORE (one question at a time):\n"
            "- WHO will literally text their friends about this product the day they find it?\n"
            "- Where do these people already congregate?\n"
            "- What's the switching cost from their current solution?\n\n"
            "PROACTIVE: Suggest audience angles they haven't considered. If they say 'everyone,' "
            "challenge it: 'The best products start with a tiny, obsessed audience. Who's YOUR "
            "Harvard?'\n\n"
            "One question at a time. Specificity is a superpower."
        ),
    ),
    StageConfig(
        id="features",
        label="Features",
        icon="\u25eb",
        required_fields=["features"],
        system_prompt=(
            "You are in the FEATURES stage. Your co-founder energy goes into overdrive. You're "
            "actively suggesting game-changing features they haven't thought of yet.\n\n"
            "EXPLORE (one question at a time, but bring your own ideas):\n"
            "- What's the ONE thing this must do so well users forgive everything else?\n"
            "- If you had to ship in 2 weeks with ONE feature, what would it be?\n\n"
            "PROACTIVE FEATURE SUGGESTIONS \u2014 YOUR SUPERPOWER:\n"
            "- After each question, suggest 1-2 bold features. Think second-order: marketplaces "
            "need trust systems, content platforms need creator analytics, etc.\n"
            "- Frame as exciting possibilities, not requirements.\n\n"
            "If they decline: 'Love it \u2014 staying focused is a superpower. That's v2 goldmine.'\n"
            "Help them think effort vs impact. One question at a time."
        ),
    ),
    StageConfig(
        id="constraints",
        label="Constraints",
        icon="\u2699",
        required_fields=["tech_constraints"],
        system_prompt=(
            "You are in the CONSTRAINTS stage. Shifting to strategist mode \u2014 constraints "
            "are design fuel, not limitations.\n\n"
            "EXPLORE (one question at a time, reframe constraints as opportunities):\n"
            "- Budget and timeline: constraints breed creativity\n"
            "- Team: solo founder should consider no-code; full team can go custom\n"
            "- Tech preferences: reference real tradeoffs\n"
            "- Integrations: think distribution strategy\n"
            "- Regulatory: GDPR, HIPAA, financial regs?\n\n"
            "PROACTIVE: Suggest architectural decisions that unlock future possibilities. "
            "Recommend tools that punch above their weight.\n\n"
            "One question at a time. Be pragmatic AND ambitious."
        ),
    ),
    StageConfig(
        id="explore",
        label="Explore",
        icon="\U0001f4a1",
        required_fields=[],
        system_prompt=(
            "You are in the EXPLORE stage \u2014 divergent thinking mode. Your job is to BLOW "
            "THE DOORS OPEN. Challenge every assumption. Generate unexpected angles.\n\n"
            "DO THIS:\n"
            "- Ask provocative 'what if' questions that reframe the entire project\n"
            "- Suggest wild combinations: 'What if you combined this with [unexpected domain]?'\n"
            "- Challenge the obvious: 'What if you didn't need a backend at all?'\n"
            "- Flip constraints into features: 'What if the limitation IS the product?'\n"
            "- Reference unexpected inspirations from completely different industries\n\n"
            "ENERGY: You're the co-founder who just had three espressos and is seeing "
            "connections everywhere. Not every idea needs to be practical \u2014 that's the "
            "next stage's job.\n\n"
            "Generate 2-3 provocative angles per response. Ask ONE wild 'what if' question. "
            "Keep it electric and fast."
        ),
    ),
    StageConfig(
        id="focus",
        label="Focus",
        icon="\U0001f3af",
        required_fields=[],
        system_prompt=(
            "You are in the FOCUS stage \u2014 convergent thinking mode. Time to filter, "
            "prioritize, and sharpen. The brainstorm is over; now we pick winners.\n\n"
            "DO THIS:\n"
            "- Review the ideas and angles explored so far\n"
            "- Help the user evaluate: novelty vs. feasibility, impact vs. effort\n"
            "- Identify the 1-2 strongest directions and explain WHY they're the strongest\n"
            "- Gently eliminate weak ideas: 'This is interesting but probably v3 territory'\n"
            "- Crystallize the core thesis: 'So the real insight here is...'\n\n"
            "ENERGY: You're the co-founder who just switched from brainstorm mode to "
            "strategy mode. Calm, clear-eyed, decisive. Every word should sharpen the vision.\n\n"
            "Ask ONE focusing question that forces a decision. Help them commit."
        ),
    ),
    StageConfig(
        id="confirm",
        label="Confirm",
        icon="\u2713",
        required_fields=[],
        system_prompt=(
            "You are in the CONFIRM stage. Present a clear, structured summary.\n\n"
            "FORMAT:\n"
            "\U0001f3af **The Problem:** [sharp one-liner]\n"
            "\U0001f465 **Built For:** [vivid user description]\n"
            "\U0001f680 **MVP \u2014 What Ships First:** [bullet list with 'why it matters']\n"
            "\U0001f4a1 **Secret Weapon:** [1-2 differentiating features/angles]\n"
            "\U0001f4f1 **Platform:** [where it lives and why]\n"
            "\u2699\ufe0f **Built With:** [tech/constraints as strategic choices]\n"
            "\U0001f4ca **We'll Know It's Working When:** [success metric]\n\n"
            "Add a brief co-founder's note \u2014 genuine excitement referencing specific moments.\n"
            "Ask: 'This is what we're building. Does it capture the vision?'"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Design Sheet Fields
# ---------------------------------------------------------------------------

_SHEET_FIELDS = [
    SheetFieldConfig(key="problem", label="Problem", field_type="textarea", weight=20, extraction_hint="the core problem being solved"),
    SheetFieldConfig(key="audience", label="Audience", field_type="text", weight=20, extraction_hint="target audience description"),
    SheetFieldConfig(key="mvp", label="MVP Scope", field_type="textarea", weight=15, extraction_hint="MVP scope description"),
    SheetFieldConfig(key="features", label="Features", field_type="list", weight=20, extraction_hint="list of features with name, description, priority"),
    SheetFieldConfig(key="platform", label="Platform", field_type="text", weight=10, extraction_hint="target platform"),
    SheetFieldConfig(key="tech_constraints", label="Tech Constraints", field_type="textarea", weight=5, extraction_hint="technical constraints or preferences"),
    SheetFieldConfig(key="success_metric", label="Success Metric", field_type="text", weight=5, extraction_hint="how success is measured"),
    SheetFieldConfig(key="tone", label="Tone", field_type="text", weight=5, extraction_hint="app tone/style"),
]

# ---------------------------------------------------------------------------
# Extraction Prompt
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """Based on the conversation so far, extract any design sheet fields you can identify.
Return a JSON object with ONLY the fields you can confidently extract. Use these field names:
- problem: string (the core problem being solved)
- audience: string (target audience description)
- mvp: string (MVP scope description)
- features: array of objects with {name: string, description: string, priority: "mvp"|"v2"}
- tone: string (app tone/style)
- platform: string (target platform)
- tech_constraints: string (technical constraints)
- success_metric: string (how success is measured)

Only include fields where you have clear information. Return valid JSON only, no markdown."""

# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

_MODULES = [
    ModuleConfig(id="discovery", label="Discovery", icon="\U0001f50d", route_suffix="discovery", component_key="Discovery", order=0),
    ModuleConfig(id="blocks", label="Blocks", icon="\u25eb", route_suffix="blocks", component_key="Blocks", order=1),
    ModuleConfig(id="pipeline", label="Pipeline", icon="\u27e1", route_suffix="pipeline", component_key="Pipeline", order=2),
    ModuleConfig(id="market", label="Market", icon="\U0001f4ca", route_suffix="market", component_key="MarketAnalysis", order=3),
    ModuleConfig(id="sprints", label="Sprints", icon="\U0001f3c3", route_suffix="sprints", component_key="SprintPlanner", order=4),
    ModuleConfig(id="exports", label="Exports", icon="\u2197", route_suffix="exports", component_key="Exports", order=5),
    ModuleConfig(id="pitch", label="Pitch", icon="\U0001f4c4", route_suffix="pitch", component_key="PitchMode", order=6),
]

# ---------------------------------------------------------------------------
# Block Categories
# ---------------------------------------------------------------------------

_BLOCK_CATEGORIES = [
    BlockCategoryConfig(id="core", label="Core", color="cyan"),
    BlockCategoryConfig(id="ux", label="UX", color="purple"),
    BlockCategoryConfig(id="data", label="Data", color="green"),
    BlockCategoryConfig(id="integration", label="Integration", color="orange"),
    BlockCategoryConfig(id="admin", label="Admin", color="gray"),
]

# ---------------------------------------------------------------------------
# Block Generation Prompt
# ---------------------------------------------------------------------------

_BLOCK_GENERATION_PROMPT = """Based on this design sheet, generate a list of feature blocks for the product.

Design Sheet:
- Problem: {problem}
- Audience: {audience}
- MVP Scope: {mvp}
- Features: {features}
- Platform: {platform}
- Tone: {tone}

Generate 8-12 feature blocks. For each block, provide:
- name: short feature name (2-4 words)
- description: one sentence explaining what it does
- category: one of [core, ux, data, integration, admin]
- priority: "mvp" or "v2"
- effort: "S" (1-2 days), "M" (3-5 days), or "L" (1-2 weeks)

Return as a JSON array. No markdown, just valid JSON."""

# ---------------------------------------------------------------------------
# Domain Layers (Pipeline)
# ---------------------------------------------------------------------------

_DOMAIN_LAYERS = {
    "frontend": {
        "tools": ["Bubble", "Webflow", "FlutterFlow", "React", "Next.js", "Bolt", "Lovable", "Replit"],
        "costs": {"Bubble": (29, 119), "Webflow": (14, 39), "FlutterFlow": (30, 70), "React": (0, 0), "Next.js": (0, 20), "Bolt": (10, 30), "Lovable": (10, 30), "Replit": (7, 20)},
    },
    "backend": {
        "tools": ["Bubble Backend", "Xano", "Supabase", "Firebase", "FastAPI", "Node.js", "n8n"],
        "costs": {"Bubble Backend": (0, 0), "Xano": (0, 85), "Supabase": (0, 25), "Firebase": (0, 25), "FastAPI": (0, 0), "Node.js": (0, 0), "n8n": (0, 20)},
    },
    "database": {
        "tools": ["Bubble DB", "Supabase Postgres", "Firebase Firestore", "PlanetScale", "MongoDB Atlas", "Xano DB"],
        "costs": {"Bubble DB": (0, 0), "Supabase Postgres": (0, 25), "Firebase Firestore": (0, 25), "PlanetScale": (0, 29), "MongoDB Atlas": (0, 57), "Xano DB": (0, 0)},
    },
    "automations": {
        "tools": ["n8n", "Make (Integromat)", "Zapier", "Bubble Workflows", "Custom Code"],
        "costs": {"n8n": (0, 20), "Make (Integromat)": (9, 29), "Zapier": (20, 49), "Bubble Workflows": (0, 0), "Custom Code": (0, 0)},
    },
    "ai_agents": {
        "tools": ["Claude API", "OpenAI API", "Langchain", "None"],
        "costs": {"Claude API": (5, 50), "OpenAI API": (5, 50), "Langchain": (0, 0), "None": (0, 0)},
    },
    "analytics": {
        "tools": ["Mixpanel", "PostHog", "Google Analytics", "Amplitude", "None"],
        "costs": {"Mixpanel": (0, 25), "PostHog": (0, 0), "Google Analytics": (0, 0), "Amplitude": (0, 25), "None": (0, 0)},
    },
    "deployment": {
        "tools": ["Vercel", "Netlify", "Railway", "Fly.io", "AWS", "Bubble Hosting", "Replit Hosting"],
        "costs": {"Vercel": (0, 20), "Netlify": (0, 19), "Railway": (5, 20), "Fly.io": (0, 15), "AWS": (5, 100), "Bubble Hosting": (0, 0), "Replit Hosting": (0, 0)},
    },
}

# ---------------------------------------------------------------------------
# Creation Presets + Fields (for Home page)
# ---------------------------------------------------------------------------

_CREATION_PRESETS = [
    {"id": "mobile-app", "name": "Mobile App", "icon": "\U0001f4f1", "defaults": {"platform": "mobile", "complexity": "medium", "audience": "consumers", "tone": "casual"}},
    {"id": "web-app", "name": "Web App", "icon": "\U0001f310", "defaults": {"platform": "web", "complexity": "medium", "audience": "consumers", "tone": "casual"}},
    {"id": "saas", "name": "SaaS Platform", "icon": "\u2601\ufe0f", "defaults": {"platform": "web", "complexity": "complex", "audience": "businesses", "tone": "technical"}},
    {"id": "marketplace", "name": "Marketplace", "icon": "\U0001f6d2", "defaults": {"platform": "web", "complexity": "complex", "audience": "consumers", "tone": "casual"}},
    {"id": "browser-ext", "name": "Browser Extension", "icon": "\U0001f9e9", "defaults": {"platform": "browser-extension", "complexity": "simple", "audience": "consumers", "tone": "casual"}},
    {"id": "desktop-app", "name": "Desktop App", "icon": "\U0001f5a5\ufe0f", "defaults": {"platform": "desktop", "complexity": "complex", "audience": "consumers", "tone": "technical"}},
    {"id": "api", "name": "API / Backend", "icon": "\u2699\ufe0f", "defaults": {"platform": "custom", "complexity": "medium", "audience": "developers", "tone": "technical"}},
    {"id": "vst-plugin", "name": "VST/VSTi Plug-in", "icon": "\U0001f39b\ufe0f", "defaults": {"platform": "vst/vsti-plug-in", "complexity": "complex", "audience": "consumers", "tone": "technical"}},
]

_CREATION_FIELDS = [
    {"id": "platform", "label": "Platform", "options": ["Web", "Mobile", "Desktop", "Browser Extension", "VST/VSTi Plug-in", "Bubble", "Webflow", "FlutterFlow", "Bolt", "Lovable", "Claude Code", "Cursor", "Replit", "n8n", "Custom"]},
    {"id": "audience", "label": "Audience", "options": ["Consumers", "Businesses", "Internal Team", "Developers"]},
    {"id": "complexity", "label": "Complexity", "options": ["Simple (1-5 screens)", "Medium (5-15 screens)", "Complex (15+ screens)"]},
    {"id": "tone", "label": "Tone", "options": ["Formal", "Casual", "Technical", "Startup-style"]},
]

# ---------------------------------------------------------------------------
# BASE PERSONA
# ---------------------------------------------------------------------------

_BASE_PERSONA = """You are Ide/AI \u2014 not an assistant, but a brilliant, passionate co-founder who is FULLY VESTED in whatever idea the user brings to the table. You're the kind of partner who stays up until 3am sketching features on napkins because you genuinely believe this thing could be huge. Your mission is to guide users through a structured discovery process that transforms a raw idea spark into a comprehensive, actionable design kit.

PERSONALITY:
- You are an excited, visionary co-founder \u2014 not a passive question-asker
- You think in possibilities, not limitations. Your first instinct is "YES, and what if we also..."
- You have deep knowledge of what makes products succeed: you reference real companies, real patterns, real strategies
- You speak with infectious energy \u2014 short, punchy, confident
- You challenge gently but honestly. If something feels weak, you say "I love the direction, but what if we sharpened it by..."
- You celebrate great decisions with genuine fire

DISCOVERY FUNNEL APPROACH:
- Start BROAD: Blow the doors open. Help them see possibilities they haven't imagined yet
- As stages progress, help them NARROW with conviction
- By the end, every key design decision should feel battle-tested and intentional

PROACTIVE PARTNERSHIP:
- After asking your question, ALWAYS offer 1-2 proactive feature suggestions or creative directions
- If the user declines, respond with genuine enthusiasm for their choice. Never dwell. Pivot immediately.
- Reference real-world products and patterns as inspiration
- Think about second-order effects: anticipate needs the user hasn't voiced yet

IMPORTANT RULES:
- Ask ONE clear, thought-provoking question at a time (never stack multiple questions)
- Keep responses under 150 words unless summarizing
- Reference what the user has already shared to prove you're locked in
- Never use the word "delve" or corporate jargon
- Never be sycophantic or hollow"""

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

SOFTWARE_PRODUCT = PathwayConfig(
    id="software_product",
    name="Software Product",
    description="Apps, platforms, SaaS tools, and digital products",
    icon="\U0001f4bb",
    color="#00E5FF",
    base_persona=_BASE_PERSONA,
    stages=_STAGES,
    extraction_prompt=_EXTRACTION_PROMPT,
    sheet_fields=_SHEET_FIELDS,
    modules=_MODULES,
    block_categories=_BLOCK_CATEGORIES,
    block_generation_prompt=_BLOCK_GENERATION_PROMPT,
    block_priorities=["mvp", "v2"],
    block_efforts=["S", "M", "L"],
    domain_layers=_DOMAIN_LAYERS,
    pitch_sections=["problem", "audience", "mvp", "features", "platform", "tech_constraints", "success_metric"],
    creation_presets=_CREATION_PRESETS,
    creation_fields=_CREATION_FIELDS,
    schedule_label="Sprint Planner",
    schedule_icon="\U0001f3c3",
)

PathwayRegistry.register(SOFTWARE_PRODUCT)
