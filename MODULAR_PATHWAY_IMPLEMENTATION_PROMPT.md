# Developer Implementation Prompt — Modular Dynamic Design Kit Pathway

> ⚠️ **STATUS: Historical (pre-2026-05-23 implementation prompt)** — this prompt drove the v1 implementation (per-module sessions). Phases 1-4 of the Discovery v2 overhaul have since superseded the v1 module-session flow for new projects. Don't re-execute this prompt as-is for new work.
>
> For current Phase 5 work (Design Kit page at `/design-kit/{projectId}`): see [`TODO.md`](TODO.md) Phase 5 section.

Read MODULAR_PATHWAY_SPEC.md fully before doing anything.
Read PRD.md, ARCHITECTURE.md, and FEATURE_SPEC.md for existing system context.

Goal:
Replace the current fixed post-discovery pathway with a fully dynamic,
modular system. The AI categorizes each project and assembles a custom
module pathway from a library of 47 modules. Users review and adjust
their pathway before execution begins.

Implementation order:

Step 1 — Database
- Add primary_category and secondary_category to projects table
- Create module_pathways table
- Create module_responses table
- Write and run migrations
- Update ORM models and Pydantic schemas

Step 2 — Seed Data
- Seed all 16 concept categories with default module stacks
- Seed all 40 new module definitions with IDs, labels, groups,
  descriptions, estimated times, and lite/deep question counts
- Load partner_styles.seed.json and module_library.seed.json

Step 3 — Backend Services
- Create categorization_service.py
  - categorize_project(concept_sheet) using Claude
  - Rule-based fallback using keyword matching
- Create pathway_service.py
  - assemble_pathway, get_base_stack, run_enrichment_pass, apply_user_edits
- Create module_service.py
  - get_module_definition, get_module_system_prompt, generate_next_question
  - extract_module_output, cross_populate_fields

Step 4 — API Endpoints
- POST /api/v1/projects/{id}/categorize
- POST /api/v1/projects/{id}/pathway/assemble
- GET /api/v1/projects/{id}/pathway
- PATCH /api/v1/projects/{id}/pathway
- POST /api/v1/projects/{id}/pathway/lock
- POST /api/v1/modules/{project_id}/{module_id}/start
- POST /api/v1/modules/{project_id}/{module_id}/respond
- GET /api/v1/modules/{project_id}/{module_id}/summary
- GET /api/v1/meta/modules
- GET /api/v1/meta/categories

Step 5 — Frontend
- Create pathwayStore.ts in Zustand
- Create pages/PathwayReview.tsx
  - Module card stack with drag-and-drop (@dnd-kit/core)
  - Lite/Deep toggle per card
  - Add/remove module controls
  - Confirm Pathway button
- Create pages/ModuleSession.tsx
  - SSE streaming conversation (same pattern as discovery chat)
  - Module completion summary
  - Next Module CTA
- Create components/pathway/ModuleCard.tsx
- Create components/pathway/PathwayProgress.tsx
- Update navigation to route from discovery completion to PathwayReview

Step 6 — Integration
- Ensure all existing modules (Design Blocks Board, Pipeline Builder,
  Prompt Kit Generator, Market Analysis, Sprint Planner, Pitch Mode,
  Export System) can appear as steps in the pathway
- Ensure cross-module field pre-population works via cross_populate_fields()
- Ensure skipped modules are flagged in Export System output

Step 7 — Tests
- Unit tests for categorization_service (test all 16 categories)
- Unit tests for pathway_service enrichment signals
- Unit tests for cross_populate_fields mappings
- Integration tests for all new API endpoints
- Frontend component tests for PathwayReview and ModuleSession

Return a summary of all created and modified files when complete.

Critical rules:
- Do not break any existing functionality
- All module sessions must use the active AI partner style
- The user must never answer the same question twice (cross-population)
- Skipped modules must always be flagged in the output
- Keep the UI consistent with the existing dark glassmorphism design system
