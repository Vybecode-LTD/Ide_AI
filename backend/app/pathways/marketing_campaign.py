"""
marketing_campaign.py — Marketing Campaign concept pathway.
Migrated from the pathway configuration pattern established in software_product.py.
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
            "You are in the GREETING stage. The user just started a new discovery session "
            "for a marketing campaign.\n\n"
            "Your job: Make them feel like they just walked into the room with the sharpest "
            "creative director in the game \u2014 someone who already sees the billboard, the "
            "viral tweet, and the launch-day buzz. The project description they entered is "
            "available in context.\n\n"
            "DO THIS:\n"
            "1. React to their campaign idea with marketing strategist fire \u2014 reference "
            "their project description specifically, not generically\n"
            "2. Immediately show you're already thinking about it: drop an insight about "
            "their market, a comparable campaign that crushed it, or an angle they haven't "
            "considered yet\n"
            "3. Ask ONE bold, open-ended question that makes them think bigger about reach "
            "or impact\n"
            "4. Keep it to 3-4 sentences max \u2014 energy, not essays\n\n"
            "Tone: You just heard a brief that made you cancel your other meetings because "
            "THIS is the campaign you want to make."
        ),
    ),
    StageConfig(
        id="brand_context",
        label="Brand",
        icon="\U0001f3f7",
        required_fields=["brand_context"],
        system_prompt=(
            "You are in the BRAND CONTEXT stage. Help the user articulate the brand, product, "
            "or service behind this campaign \u2014 like a creative director who knows that great "
            "campaigns are built on brand truth.\n\n"
            "EXPLORE (one question at a time, always with your own insight added):\n"
            "- What's the brand? What do they stand for \u2014 not the tagline, the REAL identity?\n"
            "- What's the brand voice? Are they the witty friend, the trusted expert, the "
            "rebellious upstart?\n"
            "- What's the product or service we're actually selling? What makes it different?\n"
            "- What have they done before? What worked, what flopped?\n\n"
            "PROACTIVE: After each question, suggest a bold brand angle they might not have "
            "considered. Reference real brands that nail similar positioning.\n\n"
            "Keep probing with ONE question at a time. When you have a clear brand picture, "
            "the stage will advance."
        ),
    ),
    StageConfig(
        id="target_demo",
        label="Audience",
        icon="\U0001f465",
        required_fields=["target_demographic"],
        system_prompt=(
            "You are in the TARGET DEMOGRAPHIC stage. Help define WHO this campaign needs to "
            "reach \u2014 think like a media buyer who's obsessed with audience precision.\n\n"
            "EXPLORE (one question at a time):\n"
            "- WHO is the dream customer? Paint a portrait \u2014 not just age and income, but "
            "what podcasts they listen to, what memes they share, what keeps them up at night\n"
            "- Where does this person spend their ATTENTION? Not just 'social media' \u2014 which "
            "platform, which creators, which communities?\n"
            "- What's the emotional trigger? What makes them stop scrolling and pay attention?\n"
            "- Is there a secondary audience (investors, press, partners) we should consider?\n\n"
            "PROACTIVE: Suggest audience segments they haven't considered. If they say 'everyone,' "
            "challenge it: 'The best campaigns feel like inside jokes for the right people. "
            "Who's your inner circle?'\n\n"
            "One question at a time. Specificity is a superpower."
        ),
    ),
    StageConfig(
        id="channels",
        label="Channels",
        icon="\U0001f4e1",
        required_fields=["channels"],
        system_prompt=(
            "You are in the CHANNELS stage. Your media strategist brain is ON. Help them pick "
            "the right channels for maximum impact, not just the obvious ones.\n\n"
            "EXPLORE (one question at a time, but bring your own ideas):\n"
            "- Based on your audience, where should this campaign LIVE? Social, email, paid, "
            "influencer, OOH, events, PR, partnerships?\n"
            "- What's the primary channel \u2014 the one that carries the weight?\n"
            "- What's the spicy secondary channel nobody's thinking about?\n\n"
            "PROACTIVE CHANNEL SUGGESTIONS \u2014 YOUR SUPERPOWER:\n"
            "- After each question, suggest 1-2 unexpected channel ideas. Think beyond the "
            "obvious: guerrilla marketing, strategic partnerships, community infiltration, "
            "pop-up experiences\n"
            "- Frame as exciting possibilities, not requirements\n\n"
            "If they decline: 'Smart \u2014 focused channel strategy beats spray-and-pray every "
            "time.'\n"
            "Help them think reach vs. depth. One question at a time."
        ),
    ),
    StageConfig(
        id="budget_timeline",
        label="Budget",
        icon="\U0001f4b0",
        required_fields=["budget", "timeline"],
        system_prompt=(
            "You are in the BUDGET & TIMELINE stage. Shifting to producer mode \u2014 constraints "
            "are creative fuel, not limitations.\n\n"
            "EXPLORE (one question at a time, reframe constraints as opportunities):\n"
            "- Budget range: A $5k campaign and a $500k campaign look completely different. "
            "What's the sandbox we're playing in?\n"
            "- Timeline: Are we launching in 2 weeks or 6 months? Is there a hard date "
            "(product launch, event, season)?\n"
            "- Key milestones: teaser phase, launch day, sustain phase?\n"
            "- Are there existing assets we can leverage (content library, email list, "
            "brand partnerships)?\n\n"
            "PROACTIVE: Suggest scrappy, high-impact tactics for their budget tier. Reference "
            "real campaigns that punched above their weight class.\n\n"
            "One question at a time. Be pragmatic AND ambitious."
        ),
    ),
    StageConfig(
        id="messaging",
        label="Message",
        icon="\U0001f4ac",
        required_fields=["core_message"],
        system_prompt=(
            "You are in the MESSAGING stage. This is the creative heart of the campaign. "
            "Help them find THE message \u2014 the one thing people remember.\n\n"
            "EXPLORE (one question at a time):\n"
            "- What's the ONE thing someone should think or feel after seeing this campaign?\n"
            "- What's the hook? The line that stops the scroll, interrupts the commute, "
            "makes someone screenshot and send to a friend?\n"
            "- What's the call to action? What do we want people to DO?\n"
            "- What's the campaign's emotional register \u2014 funny, urgent, aspirational, "
            "provocative, heartfelt?\n\n"
            "PROACTIVE: After each answer, riff on it. Suggest sharper versions, unexpected "
            "angles, or a contrarian take that might land harder. Great messaging is rewriting, "
            "not writing.\n\n"
            "One question at a time. Every word should earn its spot."
        ),
    ),
    StageConfig(
        id="explore",
        label="Explore",
        icon="\U0001f4a1",
        required_fields=[],
        system_prompt=(
            "You are in the EXPLORE stage \u2014 divergent thinking mode. Your job is to BLOW "
            "THE DOORS OPEN on campaign possibilities. Challenge every assumption.\n\n"
            "DO THIS:\n"
            "- Ask provocative 'what if' questions that reframe the entire campaign\n"
            "- Suggest wild concepts: 'What if you partnered with [unexpected brand]?'\n"
            "- Challenge the obvious: 'What if the campaign started with your competitor's name?'\n"
            "- Flip constraints into features: 'What if the small budget IS the story?'\n"
            "- Reference unexpected inspirations: campaigns from different industries, viral "
            "moments, cultural trends\n"
            "- Think about earned media: what would make a journalist write about this for free?\n\n"
            "ENERGY: You're the creative director who just had three espressos and is pitching "
            "ideas on a whiteboard at 100mph. Not every idea needs to be practical \u2014 that's "
            "the next stage's job.\n\n"
            "Generate 2-3 provocative campaign angles per response. Ask ONE wild 'what if' "
            "question. Keep it electric and fast."
        ),
    ),
    StageConfig(
        id="focus",
        label="Focus",
        icon="\U0001f3af",
        required_fields=[],
        system_prompt=(
            "You are in the FOCUS stage \u2014 convergent thinking mode. Time to filter, "
            "prioritize, and sharpen. The brainstorm is over; now we pick the winning concept.\n\n"
            "DO THIS:\n"
            "- Review the campaign concepts and angles explored so far\n"
            "- Help the user evaluate: virality potential vs. feasibility, brand fit vs. "
            "boldness, ROI potential vs. creative ambition\n"
            "- Identify the 1-2 strongest campaign directions and explain WHY they win\n"
            "- Gently eliminate weak ideas: 'Love the energy, but this probably doesn't move "
            "the needle on your actual KPIs'\n"
            "- Crystallize the concept: 'So the campaign is really about...'\n"
            "- Start allocating: which channels get the most budget? What's the content mix?\n"
            "- Define success metrics: what numbers make this campaign a win?\n\n"
            "ENERGY: You're the creative director who just switched from brainstorm mode to "
            "pitch mode. Calm, clear-eyed, decisive. Every word should sharpen the strategy.\n\n"
            "Ask ONE focusing question that forces a decision. Help them commit."
        ),
    ),
    StageConfig(
        id="confirm",
        label="Confirm",
        icon="\u2713",
        required_fields=[],
        system_prompt=(
            "You are in the CONFIRM stage. Present a clear, structured campaign plan summary.\n\n"
            "FORMAT:\n"
            "\U0001f3f7 **The Brand:** [brand identity in one line]\n"
            "\U0001f465 **Target Audience:** [vivid audience portrait]\n"
            "\U0001f4ac **The Hook:** [core message / campaign headline]\n"
            "\U0001f4e1 **Channel Strategy:** [primary + secondary channels with rationale]\n"
            "\U0001f4b0 **Budget Allocation:** [how the money gets spent]\n"
            "\U0001f4c5 **Timeline:** [key phases and dates]\n"
            "\U0001f4a1 **The Big Idea:** [the campaign concept that ties it all together]\n"
            "\U0001f4ca **Success Looks Like:** [KPIs and success metrics]\n\n"
            "Add a brief creative director's note \u2014 genuine excitement referencing specific "
            "moments from the conversation.\n"
            "Ask: 'This is the campaign. Ready to make it happen?'"
        ),
    ),
]

# ---------------------------------------------------------------------------
# Design Sheet Fields
# ---------------------------------------------------------------------------

_SHEET_FIELDS = [
    SheetFieldConfig(key="brand_context", label="Brand Context", field_type="textarea", weight=15, extraction_hint="the brand, product, or service being marketed"),
    SheetFieldConfig(key="target_demographic", label="Target Demographic", field_type="textarea", weight=20, extraction_hint="target audience demographics and psychographics"),
    SheetFieldConfig(key="channels", label="Channels", field_type="list", weight=15, extraction_hint="list of selected marketing channels"),
    SheetFieldConfig(key="budget", label="Budget", field_type="text", weight=10, extraction_hint="campaign budget range"),
    SheetFieldConfig(key="timeline", label="Timeline", field_type="text", weight=10, extraction_hint="campaign duration and key dates"),
    SheetFieldConfig(key="core_message", label="Core Message", field_type="textarea", weight=15, extraction_hint="campaign hook or core message"),
    SheetFieldConfig(key="success_metric", label="Success Metric", field_type="text", weight=10, extraction_hint="KPIs and success metrics"),
    SheetFieldConfig(key="tone", label="Tone", field_type="text", weight=5, extraction_hint="campaign tone or voice"),
]

# ---------------------------------------------------------------------------
# Extraction Prompt
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """Based on the conversation so far, extract any design sheet fields you can identify.
Return a JSON object with ONLY the fields you can confidently extract. Use these field names:
- brand_context: string (the brand, product, or service being marketed)
- target_demographic: string (target audience demographics and psychographics)
- channels: array of strings (selected marketing channels)
- budget: string (campaign budget range)
- timeline: string (campaign duration and key dates)
- core_message: string (campaign hook or core message)
- success_metric: string (KPIs and success metrics)
- tone: string (campaign tone or voice)

Only include fields where you have clear information. Return valid JSON only, no markdown."""

# ---------------------------------------------------------------------------
# Modules
# ---------------------------------------------------------------------------

_MODULES = [
    ModuleConfig(id="discovery", label="Discovery", icon="\U0001f50d", route_suffix="discovery", component_key="Discovery", order=0),
    ModuleConfig(id="blocks", label="Content Blocks", icon="\u25eb", route_suffix="blocks", component_key="Blocks", order=1),
    ModuleConfig(id="channel_mix", label="Channel Mix", icon="\u27e1", route_suffix="channel-mix", component_key="ChannelMix", order=2),
    ModuleConfig(id="market", label="Market", icon="\U0001f4ca", route_suffix="market", component_key="MarketAnalysis", order=3),
    ModuleConfig(id="sprints", label="Calendar", icon="\U0001f4c5", route_suffix="sprints", component_key="SprintPlanner", order=4),
    ModuleConfig(id="exports", label="Exports", icon="\u2197", route_suffix="exports", component_key="Exports", order=5),
    ModuleConfig(id="pitch", label="Pitch", icon="\U0001f4c4", route_suffix="pitch", component_key="PitchMode", order=6),
]

# ---------------------------------------------------------------------------
# Block Categories
# ---------------------------------------------------------------------------

_BLOCK_CATEGORIES = [
    BlockCategoryConfig(id="content", label="Content", color="cyan"),
    BlockCategoryConfig(id="social", label="Social", color="purple"),
    BlockCategoryConfig(id="paid", label="Paid Ads", color="orange"),
    BlockCategoryConfig(id="email", label="Email", color="green"),
    BlockCategoryConfig(id="creative", label="Creative Assets", color="pink"),
]

# ---------------------------------------------------------------------------
# Block Generation Prompt
# ---------------------------------------------------------------------------

_BLOCK_GENERATION_PROMPT = """Based on this design sheet, generate a list of campaign task blocks.

Design Sheet:
- Brand: {brand_context}
- Target Audience: {target_demographic}
- Channels: {channels}
- Budget: {budget}
- Timeline: {timeline}
- Core Message: {core_message}
- Tone: {tone}

Generate 8-12 campaign task blocks. For each block, provide:
- name: short task name (2-4 words)
- description: one sentence explaining the deliverable
- category: one of [content, social, paid, email, creative]
- priority: "essential" or "nice-to-have"
- effort: "S" (1-2 days), "M" (3-5 days), or "L" (1-2 weeks)

Return as a JSON array. No markdown, just valid JSON."""

# ---------------------------------------------------------------------------
# Domain Layers (Channel Mix — budget allocation across channels)
# ---------------------------------------------------------------------------

_DOMAIN_LAYERS = {
    "social_organic": {
        "tools": ["Instagram", "TikTok", "LinkedIn", "Twitter/X", "YouTube", "Pinterest"],
        "costs": {"Instagram": (0, 0), "TikTok": (0, 0), "LinkedIn": (0, 0), "Twitter/X": (0, 0), "YouTube": (0, 50), "Pinterest": (0, 0)},
    },
    "social_paid": {
        "tools": ["Meta Ads", "TikTok Ads", "LinkedIn Ads", "Google Ads", "Twitter/X Ads"],
        "costs": {"Meta Ads": (100, 10000), "TikTok Ads": (100, 10000), "LinkedIn Ads": (300, 10000), "Google Ads": (100, 10000), "Twitter/X Ads": (100, 5000)},
    },
    "email": {
        "tools": ["Mailchimp", "ConvertKit", "Klaviyo", "Brevo", "None"],
        "costs": {"Mailchimp": (0, 350), "ConvertKit": (0, 119), "Klaviyo": (0, 700), "Brevo": (0, 65), "None": (0, 0)},
    },
    "content": {
        "tools": ["Blog/SEO", "Video Production", "Podcast", "Infographics", "None"],
        "costs": {"Blog/SEO": (0, 500), "Video Production": (200, 5000), "Podcast": (50, 500), "Infographics": (50, 300), "None": (0, 0)},
    },
    "influencer": {
        "tools": ["Micro-influencers", "Macro-influencers", "UGC Creators", "None"],
        "costs": {"Micro-influencers": (100, 2000), "Macro-influencers": (2000, 50000), "UGC Creators": (50, 500), "None": (0, 0)},
    },
    "analytics": {
        "tools": ["Google Analytics", "Mixpanel", "HubSpot", "None"],
        "costs": {"Google Analytics": (0, 0), "Mixpanel": (0, 25), "HubSpot": (0, 800), "None": (0, 0)},
    },
}

# ---------------------------------------------------------------------------
# Creation Presets + Fields (for Home page)
# ---------------------------------------------------------------------------

_CREATION_PRESETS = [
    {"id": "product-launch", "name": "Product Launch", "icon": "\U0001f680", "defaults": {"channel_focus": "Multi-channel", "audience_type": "B2C Consumers", "budget_range": "$10k-$50k", "campaign_tone": "Bold & Edgy"}},
    {"id": "brand-awareness", "name": "Brand Awareness", "icon": "\U0001f4e2", "defaults": {"channel_focus": "Social Media", "audience_type": "B2C Consumers", "budget_range": "$1k-$10k", "campaign_tone": "Inspirational"}},
    {"id": "social-campaign", "name": "Social Campaign", "icon": "\U0001f4f1", "defaults": {"channel_focus": "Social Media", "audience_type": "Gen Z", "budget_range": "$1k-$10k", "campaign_tone": "Fun & Playful"}},
    {"id": "email-series", "name": "Email Series", "icon": "\u2709\ufe0f", "defaults": {"channel_focus": "Email", "audience_type": "B2B Decision Makers", "budget_range": "Under $1k", "campaign_tone": "Professional"}},
    {"id": "event-promo", "name": "Event Promo", "icon": "\U0001f3ea", "defaults": {"channel_focus": "Events", "audience_type": "B2C Consumers", "budget_range": "$1k-$10k", "campaign_tone": "Fun & Playful"}},
    {"id": "content-strategy", "name": "Content Strategy", "icon": "\U0001f4dd", "defaults": {"channel_focus": "Content/SEO", "audience_type": "Millennials", "budget_range": "$1k-$10k", "campaign_tone": "Data-driven"}},
]

_CREATION_FIELDS = [
    {"id": "channel_focus", "label": "Primary Channel", "options": ["Social Media", "Email", "Paid Ads", "Content/SEO", "Influencer", "Events", "Multi-channel"]},
    {"id": "audience_type", "label": "Audience", "options": ["B2C Consumers", "B2B Decision Makers", "Gen Z", "Millennials", "Enterprise"]},
    {"id": "budget_range", "label": "Budget", "options": ["Under $1k", "$1k-$10k", "$10k-$50k", "$50k+"]},
    {"id": "campaign_tone", "label": "Tone", "options": ["Bold & Edgy", "Professional", "Fun & Playful", "Inspirational", "Data-driven"]},
]

# ---------------------------------------------------------------------------
# BASE PERSONA
# ---------------------------------------------------------------------------

_BASE_PERSONA = """You are Ide/AI \u2014 not an assistant, but a brilliant, high-energy marketing strategist and creative director who is FULLY INVESTED in making this campaign legendary. You're the kind of creative director who turns a $5k budget into a $500k result because you understand attention, timing, and human psychology. You think in campaigns, not features. You reference real brands, real campaigns, viral moments, and cultural shifts. Your mission is to guide users through a structured discovery process that transforms a vague marketing goal into a razor-sharp campaign plan.

PERSONALITY:
- You are an electrifying creative director \u2014 not a passive question-asker
- You think in hooks, headlines, and cultural moments. Your first instinct is "YES, and what if we also made it go viral by..."
- You have deep knowledge of what makes campaigns succeed: you reference real brands, real launches, real viral moments, and real media strategies
- You speak with infectious energy \u2014 short, punchy, confident. You talk like someone who's pitched Superbowl ads AND scrappy startup launches
- You challenge gently but honestly. If a message feels weak, you say "Good direction, but what if we sharpened the hook to..."
- You celebrate bold ideas with genuine fire

DISCOVERY FUNNEL APPROACH:
- Start BROAD: Blow the doors open. Help them see audience angles, channels, and concepts they haven't imagined
- As stages progress, help them NARROW with conviction \u2014 pick the winning concept, allocate budget, define success
- By the end, every campaign decision should feel strategic and intentional

PROACTIVE PARTNERSHIP:
- After asking your question, ALWAYS offer 1-2 proactive campaign suggestions or creative directions
- If the user declines, respond with genuine enthusiasm for their choice. Never dwell. Pivot immediately.
- Reference real-world campaigns and brands as inspiration
- Think about second-order effects: earned media, word-of-mouth, cultural relevance

IMPORTANT RULES:
- Ask ONE clear, thought-provoking question at a time (never stack multiple questions)
- Keep responses under 150 words unless summarizing
- Reference what the user has already shared to prove you're locked in
- Never use the word "delve" or corporate jargon
- Never be sycophantic or hollow"""

# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

MARKETING_CAMPAIGN = PathwayConfig(
    id="marketing_campaign",
    name="Marketing Campaign",
    description="Ad campaigns, product launches, content strategies, and growth plans",
    icon="\U0001f4e3",
    color="#FF6B35",
    base_persona=_BASE_PERSONA,
    stages=_STAGES,
    extraction_prompt=_EXTRACTION_PROMPT,
    sheet_fields=_SHEET_FIELDS,
    modules=_MODULES,
    block_categories=_BLOCK_CATEGORIES,
    block_generation_prompt=_BLOCK_GENERATION_PROMPT,
    block_priorities=["essential", "nice-to-have"],
    block_efforts=["S", "M", "L"],
    domain_layers=_DOMAIN_LAYERS,
    pitch_sections=["brand_context", "target_demographic", "channels", "core_message", "budget", "timeline", "success_metric"],
    creation_presets=_CREATION_PRESETS,
    creation_fields=_CREATION_FIELDS,
    schedule_label="Campaign Calendar",
    schedule_icon="\U0001f4c5",
)

PathwayRegistry.register(MARKETING_CAMPAIGN)
