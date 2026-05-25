# Modular Dynamic Design Kit Pathway — Feature Specification

> ⚠️ **STATUS: Historical reference (pre-2026-05-23)** — describes the v1 modular pathway flow (Discovery → PathwayReview → PathwayExecute → per-module sessions). v1 still works for legacy projects (`projects.flow_version='v1'`) and template-created projects, but new projects default to v2's unified Discovery → Design Kit flow.
>
> For current v2 architecture: see [`CLAUDE.md`](CLAUDE.md) feature 5 + the auto-loaded project memory `discovery-v2-architecture.md`. For Phase 5 (Design Kit page) requirements: see [`TODO.md`](TODO.md) Phase 5.

## Overview

Instead of a single fixed pathway through the design kit, IdeaForge uses a
fully dynamic, modular system. After the discovery phase, the AI partner
categorizes the project and assembles a custom module pathway from a library
of 47 modules (7 existing + 40 new). The result is a design kit experience
that feels purpose-built for each individual project.

---

## How It Works — End to End

### Step 1 — Discovery Phase Completes
The existing discovery phase runs as normal. When the concept sheet reaches
sufficient confidence, the discovery phase is marked complete.

### Step 2 — AI Categorization
The AI analyzes the completed concept sheet and assigns:
- One PRIMARY concept category
- Optionally one SECONDARY category (for hybrid projects)

Categorization is stored on the project record.

### Step 3 — Base Module Stack Selection
Each category has a defined default module stack (5–9 modules). The AI
loads this base stack automatically.

### Step 4 — AI Enrichment Pass
The AI reviews specific project details from the concept sheet and adds or
removes modules based on signals. Examples:
- Mentions investors → add Revenue Model Designer + Investor Deck Outline
- Physical location mentioned → add Space Program + Footprint & Flow Diagram
- Solo builder → simplify or remove Team & Resource Planner
- Regulated industry → add Regulatory & Compliance Check
- Writing/film project → add Production Bible + Narrative & Story Arc

### Step 5 — User Review Screen
Before the pathway begins, display a visual card stack of the selected modules.
Each card shows:
- Module name
- One-line purpose
- Estimated completion time (e.g., ~5 min / ~10 min)
- Why the AI included it (one sentence)

User can:
- Remove a module
- Add a module from the full library
- Reorder modules via drag and drop
- Toggle Lite mode (3 questions) or Deep mode (10 questions) per module

### Step 6 — Pathway Execution
The user moves through modules sequentially. Each module is an AI-guided
conversation or structured form. Information collected in earlier modules
automatically pre-populates relevant fields in later modules — the user
never answers the same question twice.

### Step 7 — Design Kit Assembly
When all modules are complete, the system compiles the full Design Kit.
The existing Export System handles output formats (.md, .pdf, .docx, .txt, .zip).
The existing Prompt Kit Generator handles software/tech projects.
The existing Pitch Mode handles the shareable one-page brief.

---

## Concept Categories

Implement these 16 categories. Each project is assigned a primary and
optionally a secondary category.

| ID | Label | Examples |
|----|-------|---------|
| software_tech | Software & Tech | Apps, SaaS, APIs, tools, platforms, plugins |
| physical_product | Physical Product | Consumer goods, hardware, gadgets, manufacturing |
| built_environment | Built Environment | Houses, buildings, interiors, renovations, landscapes |
| business_startup | Business & Startup | Ventures, franchises, brick-and-mortar, service businesses |
| creative_writing | Creative Writing | Novels, screenplays, scripts, short stories, comics |
| research_academic | Research & Academic | Theories, studies, papers, experiments, formulas |
| art_visual | Art & Visual Design | Paintings, installations, graphic work, photography |
| music_audio | Music & Audio | Albums, compositions, podcasts, sound design, live shows |
| film_video | Film & Video | Short films, documentaries, YouTube series, commercials |
| food_hospitality | Food & Hospitality | Restaurants, cafes, catering, menus, food products |
| fashion_apparel | Fashion & Apparel | Clothing lines, accessories, brand identity, collections |
| education_training | Education & Training | Courses, curricula, workshops, coaching programs |
| event_experience | Event & Experience | Conferences, festivals, pop-ups, activations, exhibitions |
| health_wellness | Health & Wellness | Clinics, fitness, wellness brands, mental health programs |
| social_impact | Social Impact & Nonprofit | Charities, community programs, advocacy, NGOs |
| finance_investment | Finance & Investment | Funds, financial products, investment theses, fintech |

---

## Module Library (47 Total)

### Existing Modules (unchanged — listed for reference only)
- Design Blocks Board
- Pipeline Builder
- Prompt Kit Generator
- Market Analysis
- Sprint Planner
- Pitch Mode
- Export System

### New Modules

#### Group: Definition
- audience_persona_builder — Detailed user/customer profiles, demographics, motivations, pain points
- problem_opportunity_framer — Articulates the specific gap or need the concept addresses
- goals_success_metrics — Defines what winning looks like with measurable outcomes
- constraints_mapper — Budget, time, skills, regulations, and physical limits
- assumptions_log — Surfaces things being taken for granted that should be validated

#### Group: Research & Validation
- audience_validation_planner — Methods and questions to test assumptions about target users before building
- proof_of_concept_planner — Defines the smallest testable version and how to test it
- risk_assessment — What could go wrong, likelihood, severity, mitigation
- regulatory_compliance_check — Legal, licensing, safety, and industry-specific rules
- trend_timing_analysis — Whether the timing is right and why, relevant trend signals

#### Group: Planning
- team_resource_planner — Who and what is needed, roles, skills gaps, hiring needs
- budget_cost_estimator — Full project cost breakdown by phase (distinct from pipeline tech costs)
- dependency_mapper — What must happen before what, critical path identification
- operations_planner — Day-to-day logistics once the concept is live

#### Group: Technical (software/tech supplement)
- data_model_planner — Entities, relationships, data types, storage needs (deeper than pipeline)
- security_compliance_layer — Auth strategy, data protection, privacy, access control

#### Group: Creative & Brand
- brand_identity_framework — Name, voice, tone, visual language, core values
- design_language_guide — Color direction, typography, style references
- narrative_story_arc — Story structure for writing, film, games, or brand storytelling
- character_world_builder — Character profiles, world rules, lore (fiction, screenplays, games)
- content_strategy — What content is needed, in what format, when, and for whom
- creative_direction_brief — Visual and tonal reference points, mood board prompts

#### Group: Space & Physical
- space_program — Areas/rooms needed, their functions and spatial relationships
- materials_finish_selector — Surfaces, textures, key material choices
- footprint_flow_diagram — How people move through the space or interact with the product
- vendor_supplier_map — Who provides what physically, sourcing strategy
- equipment_inventory_list — Hardware, tools, stock, and physical assets needed

#### Group: Go-To-Market
- launch_strategy — How and when to introduce this to the world
- distribution_channel_planner — How it reaches its audience, channel mix
- pricing_strategy — How value is captured, pricing model options
- marketing_messaging_framework — What to say, where to say it, and to whom
- partnership_outreach_map — Collaborators, press, influencers, key relationships
- community_retention_plan — How to keep people engaged after launch

#### Group: Business & Finance
- revenue_model_designer — How this makes money, model options, unit economics
- financial_projection_builder — Basic P&L, break-even, cash flow, projections
- funding_investment_map — Bootstrapped, grants, investors, crowdfunding paths
- business_model_canvas — Lean one-page business structure overview
- legal_ip_planner — Entity type, IP protection strategy, key contracts needed

#### Group: Output (supplements existing Export + Pitch Mode)
- production_bible — Full reference doc: characters, world rules, tone, chapter/episode breakdowns
- investor_deck_outline — Structured framework for a funding presentation

---

## Default Module Stacks Per Category

These are the base stacks the AI loads before the enrichment pass.
Existing modules are referenced by name. New modules by ID.

### software_tech
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
constraints_mapper, Design Blocks Board, Pipeline Builder, data_model_planner,
Prompt Kit Generator, Sprint Planner, launch_strategy, Pitch Mode

### physical_product
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
constraints_mapper, risk_assessment, vendor_supplier_map, equipment_inventory_list,
budget_cost_estimator, regulatory_compliance_check, launch_strategy,
distribution_channel_planner, pricing_strategy

### built_environment
audience_persona_builder, goals_success_metrics, constraints_mapper,
space_program, materials_finish_selector, footprint_flow_diagram,
vendor_supplier_map, equipment_inventory_list, budget_cost_estimator,
dependency_mapper, operations_planner

### business_startup
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
constraints_mapper, Market Analysis, risk_assessment, revenue_model_designer,
business_model_canvas, budget_cost_estimator, launch_strategy,
marketing_messaging_framework, pricing_strategy, legal_ip_planner, Pitch Mode

### creative_writing
audience_persona_builder, goals_success_metrics, narrative_story_arc,
character_world_builder, brand_identity_framework, content_strategy,
constraints_mapper, production_bible

### research_academic
problem_opportunity_framer, goals_success_metrics, assumptions_log,
proof_of_concept_planner, risk_assessment, trend_timing_analysis,
regulatory_compliance_check, dependency_mapper

### art_visual
audience_persona_builder, goals_success_metrics, creative_direction_brief,
brand_identity_framework, design_language_guide, content_strategy,
distribution_channel_planner, pricing_strategy

### music_audio
audience_persona_builder, goals_success_metrics, narrative_story_arc,
creative_direction_brief, content_strategy, distribution_channel_planner,
pricing_strategy, partnership_outreach_map

### film_video
audience_persona_builder, goals_success_metrics, narrative_story_arc,
character_world_builder, creative_direction_brief, production_bible,
budget_cost_estimator, team_resource_planner, vendor_supplier_map,
distribution_channel_planner, launch_strategy

### food_hospitality
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
constraints_mapper, space_program, footprint_flow_diagram, vendor_supplier_map,
equipment_inventory_list, budget_cost_estimator, brand_identity_framework,
regulatory_compliance_check, launch_strategy, operations_planner

### fashion_apparel
audience_persona_builder, goals_success_metrics, brand_identity_framework,
design_language_guide, creative_direction_brief, vendor_supplier_map,
budget_cost_estimator, pricing_strategy, distribution_channel_planner,
launch_strategy, marketing_messaging_framework

### education_training
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
content_strategy, narrative_story_arc, budget_cost_estimator, pricing_strategy,
distribution_channel_planner, community_retention_plan, launch_strategy

### event_experience
audience_persona_builder, goals_success_metrics, constraints_mapper,
space_program, footprint_flow_diagram, vendor_supplier_map, budget_cost_estimator,
team_resource_planner, operations_planner, launch_strategy,
partnership_outreach_map, marketing_messaging_framework

### health_wellness
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
constraints_mapper, risk_assessment, regulatory_compliance_check,
brand_identity_framework, budget_cost_estimator, operations_planner,
launch_strategy, community_retention_plan

### social_impact
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
assumptions_log, risk_assessment, funding_investment_map, legal_ip_planner,
partnership_outreach_map, marketing_messaging_framework, operations_planner,
community_retention_plan, Pitch Mode

### finance_investment
audience_persona_builder, problem_opportunity_framer, goals_success_metrics,
constraints_mapper, risk_assessment, regulatory_compliance_check,
revenue_model_designer, financial_projection_builder, funding_investment_map,
business_model_canvas, legal_ip_planner, investor_deck_outline, Pitch Mode

---

## AI Enrichment Signals

After loading the base stack, the AI checks the concept sheet for these
signals and adjusts the module stack accordingly.

| Signal (detected in concept sheet) | Action |
|------------------------------------|--------|
| Mentions investors or fundraising | Add: revenue_model_designer, investor_deck_outline, financial_projection_builder |
| Mentions physical location or space | Add: space_program, footprint_flow_diagram |
| Mentions solo builder or no team | Simplify: team_resource_planner → flag as optional |
| Mentions regulated industry (medical, food, finance, legal) | Add: regulatory_compliance_check |
| Mentions brand or identity | Add: brand_identity_framework, design_language_guide |
| Mentions existing competition | Add: Market Analysis (if not already in stack) |
| Mentions timeline or deadline pressure | Add: dependency_mapper, Sprint Planner |
| Mentions content creation | Add: content_strategy |
| Mentions partnerships or press | Add: partnership_outreach_map |
| Secondary category is software_tech | Add: Pipeline Builder, Prompt Kit Generator |
| Secondary category is business_startup | Add: revenue_model_designer, business_model_canvas |
| Very early concept (low confidence score) | Add: assumptions_log, proof_of_concept_planner |

---

## Database Changes

### projects table
Add columns:
- primary_category (string, enum of 16 category IDs)
- secondary_category (string, nullable, same enum)
- pathway_locked (boolean, default false) — true once user confirms module stack

### module_pathways table (new)
Columns:
- id (UUID PK)
- project_id (UUID FK)
- modules (JSONB) — ordered array of module IDs
- lite_deep_settings (JSONB) — per-module lite/deep preference
- status (enum: pending | active | complete)
- created_at, updated_at

### module_responses table (new)
Columns:
- id (UUID PK)
- project_id (UUID FK)
- module_id (string)
- responses (JSONB) — collected answers
- completed (boolean)
- completed_at (timestamp)
- created_at

---

## API Changes

### Categorization
POST /api/v1/projects/{id}/categorize
- Triggers AI categorization of the concept
- Returns primary_category, secondary_category, confidence

### Pathway Assembly
POST /api/v1/projects/{id}/pathway/assemble
- Loads base stack for category
- Runs enrichment pass
- Returns ordered module list with metadata

GET /api/v1/projects/{id}/pathway
- Returns current pathway state, module order, completion status per module

PATCH /api/v1/projects/{id}/pathway
- Accepts user edits to module order, additions, removals
- Body: { modules: [...], lite_deep_settings: {...} }

POST /api/v1/projects/{id}/pathway/lock
- Locks the pathway and begins execution

### Module Execution
POST /api/v1/modules/{project_id}/{module_id}/start
- Initializes a module session, returns first AI question

POST /api/v1/modules/{project_id}/{module_id}/respond
- Accepts user response, returns next question or completion signal

GET /api/v1/modules/{project_id}/{module_id}/summary
- Returns structured summary of completed module responses

### Module Library Metadata
GET /api/v1/meta/modules
- Returns full module library with IDs, labels, groups, descriptions, estimated times

GET /api/v1/meta/categories
- Returns all 16 categories with default module stacks

---

## Backend Services

### New: categorization_service.py
- categorize_project(concept_sheet) -> { primary, secondary, confidence }
- Uses Claude to read the concept sheet and assign categories
- Falls back to rule-based keyword matching if confidence is low

### New: pathway_service.py
- assemble_pathway(project, primary_category, secondary_category) -> List[module_id]
- get_base_stack(category) -> List[module_id]
- run_enrichment_pass(base_stack, concept_sheet) -> List[module_id]
- apply_user_edits(pathway, edits) -> List[module_id]

### New: module_service.py
- get_module_definition(module_id) -> dict
- get_module_system_prompt(module_id, concept_sheet, ai_partner_style) -> str
- generate_next_question(module_id, session_state) -> str
- extract_module_output(module_id, responses) -> dict
- cross_populate_fields(completed_modules) -> dict
  - Ensures answers from earlier modules pre-fill later modules

---

## Frontend Changes

### New: pages/PathwayReview.tsx
- Full-screen module card stack review page
- Shows each module card with name, purpose, estimated time, and AI reasoning
- Drag-and-drop reorder via @dnd-kit/core
- Add/remove module controls
- Lite/Deep toggle per module card
- "Confirm Pathway" button → locks and starts

### New: components/pathway/ModuleCard.tsx
- Card UI for pathway review and execution
- States: pending / active / complete / skipped

### New: components/pathway/PathwayProgress.tsx
- Sidebar or top-of-page progress indicator
- Shows all modules in the pathway, current position, completion status

### New: pages/ModuleSession.tsx
- Single module execution page
- Renders AI questions as a guided conversation or structured form
- Uses SSE streaming (same pattern as discovery chat)
- Shows module completion summary when done
- "Next Module" CTA

### Updated: Zustand store (pathwayStore.ts)
- currentPathway: module list with status per module
- activeModuleId
- moduleResponses: map of module_id to collected answers
- pathwayComplete: boolean
- setPathway, updateModuleStatus, setActiveModule, saveResponse

---

## Cross-Module Intelligence Rules

When a module completes, the module_service.cross_populate_fields() function
runs and pre-fills the following field mappings:

| Source module | Field | Pre-fills in |
|---|---|---|
| audience_persona_builder | audience description | Market Analysis, launch_strategy, marketing_messaging_framework, pricing_strategy |
| problem_opportunity_framer | problem statement | goals_success_metrics, risk_assessment, Market Analysis |
| goals_success_metrics | success metrics | Sprint Planner, financial_projection_builder, investor_deck_outline |
| constraints_mapper | budget range | budget_cost_estimator, financial_projection_builder |
| brand_identity_framework | brand voice/tone | creative_direction_brief, content_strategy, marketing_messaging_framework |
| risk_assessment | key risks | assumptions_log, regulatory_compliance_check, investor_deck_outline |
| revenue_model_designer | revenue model | financial_projection_builder, business_model_canvas, pricing_strategy |

---

## Module Skipping Rule

If a user skips a module:
- Record it as "skipped" in module_responses
- Flag the gap in the final Design Kit output with a note:
  "[Module name] was skipped. This section may be incomplete."
- The AI should reference skipped modules during export and suggest
  the user revisit them before finalizing

---

## Lite vs. Deep Mode Per Module

Each module supports two modes:

Lite mode:
- 2–3 focused questions
- Fast completion (~3–5 min)
- Covers the essentials only

Deep mode:
- 6–10 questions
- Thorough exploration (~10–20 min)
- Covers nuances, edge cases, and extended detail

The user selects mode per module on the PathwayReview screen.
The AI adjusts its question depth and follow-up behavior accordingly.
Default: Lite for straightforward modules, Deep for complex ones
(e.g., financial_projection_builder defaults to Deep).

---

## Acceptance Criteria

Feature is complete when:
- AI correctly categorizes at least 90% of test projects to the right primary category
- Base module stacks load correctly for all 16 categories
- Enrichment signals correctly add/remove modules based on concept sheet content
- PathwayReview screen renders all module cards with correct metadata
- Users can add, remove, and reorder modules before locking
- Lite/Deep mode toggle affects question count and depth per module
- Module sessions run as SSE conversations using the active AI partner style
- Cross-module field pre-population works across all defined mappings
- Skipped modules are flagged in the final Design Kit output
- All new endpoints return correct responses and error states
- All new tables are migrated and seeded
- Existing modules (Design Blocks Board, Pipeline Builder, etc.) are
  unaffected and integrate cleanly as pathway steps
