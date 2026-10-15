# Features: Ide/AI

> Moved verbatim from `CLAUDE.md` on 2026-10-15 (lean-context pass). Section numbers are unchanged, so a citation such as `CLAUDE.md §5a` is found here by its heading.

> Moved from `CLAUDE.md` on 2026-10-15.

## Features

### 1. Authentication & User Management (Clerk)
- **Clerk-managed** sign-in/sign-up (email/password + Google, Microsoft, GitHub OAuth)
- Clerk webhook syncs users to local DB (`clerk_webhook.py`)
- Backend verifies Clerk session JWTs via JWKS (`core/clerk.py`)
- Frontend uses `@clerk/clerk-react` — `SignInPage.tsx`, `SignUpPage.tsx`
- `ProtectedRoute` uses Clerk's `useAuth()` hook
- `apiClient.ts` attaches Clerk session token via `getToken()`
- Avatar upload (JPEG/PNG/WebP, max 2MB, stored as base64 data URI)
- Per-user persistent memory injected into AI context
- Endpoints: `GET /auth/me`, `PATCH /auth/me`, `POST /auth/me/avatar`, `GET /auth/me/entitlements`

### 1b. Stripe Billing + Entitlements
- Checkout sessions for subscription plans (Basic Monthly/Yearly, Pro Monthly/Yearly)
- Billing portal for managing subscriptions
- Stripe webhook syncs customer ID and subscription status
- `CheckoutRedirect.tsx` handles post-checkout flow
- `Profile.tsx` has "Manage Billing" button
- `Landing.tsx` has pricing section with Upgrade buttons
- Entitlement service: plan-based limits (free: 3 projects / basic: 25 / pro: unlimited)
- Feature gates on project creation, prompt kit generation, and market analysis
- Endpoints: `POST /billing/checkout`, `POST /billing/portal`, `POST /billing/webhook`
- DB: `stripe_customer_id` on users (migration 019), subscription state columns (migration 032)

### 2. Project System
- Single text input for idea description
- Configuration selectors: platform, audience, complexity, tone, pathway, AI partner style
- Platform options: Bubble, Webflow, FlutterFlow, Bolt, Lovable, Claude Code, Cursor, Replit, n8n, Custom
- Audience options: Consumers, Businesses, Internal Team, Developers
- Complexity: Simple (1–5 screens), Medium (5–15), Complex (15+)
- Tone: Formal, Casual, Technical, Startup-style
- Snapshot-based version history (JSONB), auto-saves at milestones, restore any version
- Multi-user project sharing with feedback/ratings
- Template-based creation from ~25 seed templates across 16 categories
- DB: `projects` table — UUID PK, user_id FK, name, accent color, platform, pathway_id, ai_partner_style

### 3. Concept Pathways
- Domain-specific project types that customize the entire discovery experience
- 4 pathways: Software Product (default), Marketing Campaign, Brand Identity, Creative Writing
- Each pathway defines: base_persona, discovery_stages (divergent/convergent), sheet_schema, creation_fields, creation_presets
- AI auto-detection: `POST /pathways/detect` analyzes idea and recommends pathway
- Registry: `backend/app/services/pathway_service.py`, served via `GET /pathways`
- DB: `pathway_id` column on projects (migration 009)

### 4. AI Partner Selector
- 10 collaboration styles that change actual AI behavior (not cosmetic)
- Partners: Creative, Intellectual, Trailblazer, Strategist (DEFAULT), Architect, Coach, Skeptic, Visionary, Editor, Scientist
- 3-layer prompt composition: (1) Base pathway persona → (2) Partner style fragment → (3) Session context
- Each fragment has Core Behaviour, Questioning Style, and Guardrails sections
- Partners change HOW the AI collaborates — structured output schema is NEVER altered by partner choice
- Mid-session switching: `PATCH /discovery/{session_id}/partner` — preserves chat + sheet, applies to future replies only
- Metadata: `GET /meta/partner-styles` — frontend fetches from backend, never hardcoded
- Home page: inline 5x2 glassmorphism preset grid (not a modal)
- Discovery page: ActivePartnerBadge in header, PartnerSelector modal for mid-session switch
- DB: `ai_partner_style` on projects + sessions (migration 010)

### 5. AI Discovery Chat
- SSE streaming via FastAPI StreamingResponse + EventSource on frontend
- **Branches on `project.flow_version`**:
  - **v1 (legacy projects)**: State machine stages (greeting → problem → audience → features → constraints → confirm). After each AI response the backend extracts design-sheet fields, writes to `design_sheets`, emits `sheet_update` event. This is the original behavior — untouched.
  - **v2 (new projects)**: Unified prompt that targets ALL module field schemas at once. The AI sees every assembled module + its fields + what's already filled, and funnels toward the first unfilled REQUIRED field each turn. After each response the backend runs `extract_module_fields` and writes per-module field values into `module_responses.responses`. Emits a `field_update` SSE event containing per-field updates + an aggregate summary (overall %, required %, per-module breakdown).
- Event types: `token` (streaming text), `sheet_update` (v1 only), `field_update` (v2 only), `done` (response complete; always emitted, hardened with try/except + fallback chips)
- Quick reply chips: AI-generated suggested replies per turn (`[CHIPS: a | b | c]` extracted with 3-stage fallback chain)
- Voice input: Web Speech API mic button next to chat input (browser-only, zero backend cost)
- UI: left stage stepper, center chat thread, right side panel branches on `flow_version`:
  - **v1**: `DesignSheetPanel` (`components/framework/DesignSheetPanel.tsx`) showing extracted design-sheet fields + confidence ring
  - **v2**: `ProgressPanel` (`components/discovery/ProgressPanel.tsx`) showing overall %, expandable per-module breakdown with filled/required-left/optional-left counts, accent highlight on just-filled fields
- Proceed button gate also branches:
  - **v1**: appears when `sheet.confidence_score >= 70`, routes to `/pathway-review/{id}`
  - **v2**: always available once `summary.required_total > 0`, routes to `/exports/{id}` (interim Design Kit destination — Phase 5 swaps to `/design-kit/{id}`). Warning chip shows live `required_filled / required_total` percentage when below 80%.
- `useSSE` hook accepts `onFieldUpdate` callback alongside `onSheetUpdate` — exports `FieldUpdate`, `FieldSummary`, `FieldUpdatePayload` types
- v2 greeting uses a dedicated `build_unified_greeting_prompt` that references the assembled modules + steers toward the first required field's extraction hint. v1 keeps the legacy `build_greeting_prompt`.
- v2 ProgressPanel hydrates on mount via `GET /discovery/{session_id}/field-summary` so resume mid-session shows accurate progress without waiting for the next message.
- v2 Discovery hides the stage UI (TopBar subtitle, left StagesStepper, mobile stage indicator) — the unified flow has no stage progression.
- AI model: Anthropic Claude (claude-sonnet-4-6), configurable via CLAUDE_MODEL env var
- Designed for 15–30 minute sessions from idea to completed design kit

### 6. Design Sheet
- Structured data auto-populated from discovery conversation in real time
- Fields: problem, audience, MVP scope, features (JSONB), tone, platform, constraints, plus pathway-specific fields
- Updated via sheet_update SSE events, frontend syncs via Zustand store
- DB: `design_sheets` table

### 7. Design Blocks Board
- AI generates 8–12 feature cards from completed design sheet
- Card properties: title, description, category, priority (MVP/V2), effort (S/M/L), sort order
- Drag-and-drop via @dnd-kit/core
- Scope slider: Lean / Balanced / Full filters visible blocks
- Right panel: Prompt Kit Preview showing how blocks translate to platform prompts
- Actions: regenerate blocks, add custom block
- DB: `blocks` table

### 8. Pipeline Builder
- 7 infrastructure layers: Frontend, Backend, Database, Automations, AI/Agents, Analytics, Deployment
- AI recommends tools per layer based on project requirements
- Curated tool options per layer with cost/complexity metadata
- Cost estimation: min/max USD/month range
- Compatibility checking with notes on tool interplay
- Swap any tool → AI re-evaluates compatibility
- UI skeleton generation: JSON screen list + nav flow + component inventory
- UI: horizontal scrollable canvas, SVG connector lines, right cost/compatibility panel
- DB: `pipeline_nodes` table

### 9. Prompt Kit Generator
- Structured, copyable prompt blocks formatted for the user's specific builder platform
- Sections: System Context, App Description, Feature List, Data Model, Constraints, First Task
- 7 platform templates (Jinja2) — each written in that platform's expected format/terminology:
  - Bubble: data type definitions + workflow instructions
  - Claude Code: database schemas, API endpoints, phased implementation plan
  - Bolt: single paste-ready prompt + follow-up prompts for iteration
  - + Webflow, FlutterFlow, Cursor, Replit
- Zero Dev Language Mode: rewrites prompts in jargon-free plain language
- Actions: copy all, copy section, regenerate
- DB: `prompt_kits` table

### 10. Market Analysis
- AI-driven competitive analysis, streamed via SSE
- Endpoint: `POST /market/{project_id}/generate`
- DB: `market_analyses` table (migration 002)

### 11. Sprint Planner
- Auto-generated development sprint plans from design sheet + feature blocks
- Ownership verification on get/update/delete
- Endpoint: `POST /sprints/{project_id}/generate`
- DB: `sprint_plans` table (migrations 007, 008)

### 12. Pitch Mode
- Clean, shareable one-page project brief
- Content: title, value proposition, audience, features (3–5), MVP scope, flow diagram
- Flow diagram: React Flow (read-only), 4–6 nodes from blocks
- Sharing: toggle public link, copy URL, set expiry
- Export: print/PDF via browser print API

### 13. Export System
- Formats: Markdown (.md), plain text (.txt), PDF (.pdf), Word (.docx), ZIP (all formats)
- Platform-specific Jinja2 templates
- Market analysis export: PDF, DOCX, TXT via `GET /market/{id}/export?format=pdf|docx|txt`
- Endpoint: `GET /projects/{id}/export?format=md|pdf|docx|zip`

### 14. Modular Dynamic Design Kit Pathway
- AI categorizes projects into 16 concept categories (software, food, film, fashion, etc.)
- Each category has a unique default module set drawn from a library of 40 modules
- Categorization uses project name + description + concept sheet fields for accurate classification
- Pathway assembly: base stack (from category) → enrichment pass (signals from concept sheet) → user review
- Users can reorder, add/remove modules, toggle Lite (2–3 questions) / Deep (6–10 questions) per module
- Cross-module intelligence: 7 field mapping rules pre-populate answers from earlier modules
- SSE-streamed AI conversations per module with `[MODULE_COMPLETE]` and `[CHIPS:]` markers
- Seed data: `concept_categories.seed.json` (16 categories), `module_library.seed.json` (47 modules)
- Backend: `categorization_service.py`, `modular_pathway_service.py`, `module_service.py`
- Routers: `module_pathway.py` (categorize/assemble/review/lock), `modules.py` (start/respond/skip/summary)
- Frontend: `PathwayReview.tsx`, `PathwayExecute.tsx`, `ModuleSession.tsx`, `modulePathwayStore.ts`
- DB: `module_pathways` table, `module_responses` table (migration 011)

### 15. Ambient Guidance Tutorial System
- Three components: StageInterlude (phase transition cards), PulseBeacon (attention rings), Whisper (contextual tips)
- Integrated into 7 pages: Home, Discovery, PathwayReview, PathwayExecute, ModuleSession, Exports, Settings
- Dismissals persisted via Zustand + localStorage (`ideaforge-tutorial` key)
- Reset button in Settings page clears all tutorial state
- Components: `frontend/src/components/tutorial/` (StageInterlude, PulseBeacon, Whisper)
- Store: `frontend/src/stores/tutorialStore.ts`

### 16. Project Folder System
- Persistent sidebar folder tree
- Sections per project: Discovery Notes, Design Sheet, Prompt Kit, Pipeline Map, Exports, Versions
- Version timeline dots, click to restore any snapshot
- Actions: New Project, Duplicate, Archive

### 17. Email Verification (Legacy — now handled by Clerk)
- Previously used custom 6-digit codes via Resend API
- Now handled entirely by Clerk's built-in email verification
- DB tables (`email_verifications`, `password_resets`) still exist but are unused
- Migrations 012, 020 created these tables — kept for migration chain integrity

### 18. User Profiles
- Dedicated profile page (`/profile`) with avatar upload, bio editor, project stats
- Avatar: uploaded image (JPEG/PNG/WebP, max 2MB) or generated initials fallback
- Account type badge (free/pro)
- Sidebar profile container: avatar circle, display name, plan badge, link to profile
- Centralized `authStore` (Zustand) — `user`, `fetchUser()`, `updateUser()`, `logout()`, `initials()`
- Backend: `POST /auth/me/avatar`, `PATCH /auth/me` for profile updates
- DB: `account_type`, `bio` columns (migration 013)

### 19. Idea Inbox
- Email-to-idea pipeline: users get a unique `inbox_email` address
- Inbound emails parsed via Resend webhook → `IdeaInboxItem` records
- Manual idea capture also supported
- Per-item: choose AI partner style, promote to full project ("Build"), or delete
- Sidebar shows unread inbox count badge — updated in realtime via SSE stream (Redis pub/sub backed). Falls back to a one-shot fetch on mount when Redis isn't configured (`REDIS_URL` empty → endpoint returns 503).
- Realtime architecture: `app/services/inbox_pubsub.py` publishes to `inbox:user:{user_id}` channel on every mutation; `GET /inbox/stream` opens an SSE subscription for the authenticated user and pushes `hello` (initial count) + `update` events as they happen
- Endpoints: `GET /inbox`, `POST /inbox`, `GET /inbox/count`, `GET /inbox/stream` (SSE), `POST /inbox/{id}/promote`, `DELETE /inbox/{id}`
- Webhook: `POST /webhooks/inbound-email` (publishes to pubsub after creating the row)
- Frontend: `inboxStore` (Zustand) manages connection + auto-reconnect with exponential backoff; Sidebar wires `connectStream()` / `disconnectStream()` to mount/unmount
- DB: `idea_inbox_items` table, `inbox_email` on users (migration 014)
- Required env var (production): `REDIS_URL` — without it, the stream returns 503 and the frontend falls back to mount-time fetches only

### 20. Sharing Feedback & Ratings
- Project shares can enable comments and/or star ratings via toggles
- Viewers can leave threaded comments and rate individual feature blocks (1–5 stars)
- Owner sees aggregated feedback in a FeedbackPanel
- ShareDialog has "Allow Comments" and "Allow Feature Ratings" toggles
- Endpoints: `POST/GET /sharing/public/{token}/comments`, `POST/GET /sharing/public/{token}/ratings`
- DB: `share_comments`, `block_ratings` tables, `allow_feedback`/`allow_ratings` on `project_shares` (migration 015)

### 21. Project Templates
- ~25 seed templates across all 16 concept categories (Coffee Shop, iOS App, Short Film, Online Course, SaaS Platform, Podcast, E-commerce, etc.)
- Displayed in a category-grouped TemplateGrid on the Home page
- Selecting a template pre-populates design sheet fields at ~40% confidence
- Seed data: `project_templates.seed.json`
- Endpoint: `GET /templates`

### 22. Voice Discovery
- Browser Web Speech API — zero backend cost
- `useVoiceInput` hook: `isListening`, `transcript`, `isSupported`, `startListening`, `stopListening`, `resetTranscript`
- VoiceMicButton component with pulsing animation, hidden when browser doesn't support
- Real-time transcript populates the Discovery chat input

### 23. Concept Branching
- Git-like project forking for exploring alternative directions
- Deep-copies project and all child records into a new branch
- Compare two branches side-by-side
- Merge branch back into parent
- Branch indicators visible in Library page
- Endpoints (router prefix `/branching`): `POST /branching/{project_id}/branch`, `POST /branching/{project_id}/merge/{branch_id}`, `GET /branching/{project_id}/branches`, `GET /branching/{project_id}/compare/{branch_id}`
- DB: `concept_branches` table (migration 016)

### 24. External Integrations (Notion live; others coming soon)
- 6 providers: **Notion (LIVE in production since 2026-05-31)**, Trello, Linear, Figma, Google Docs, Airtable (still `status: "coming_soon"`)
- **Notion (first live integration)** — full 3-legged OAuth + "push design kit to a Notion page":
  - `app/services/notion_service.py`: `is_configured()`, `build_authorize_url()`, `exchange_code_for_token()` (HTTP Basic, secret stays server-side), a **pure** `render_design_kit_blocks()` (unified v1/v2 artifact context → Notion blocks), and REST IO `create_design_kit_page()` (100-child batching) / `list_accessible_pages()`
  - OAuth: `POST /integrations/notion/authorize` mints a signed-`state` JWT (HS256, scope `notion_oauth`, 10-min TTL, secret falls back SHARE_ACCESS_SECRET → CLERK_SECRET_KEY); `GET /integrations/notion/callback` is **public** (browser redirect — auth rides in the verified `state`), exchanges the code, stores the token **Fernet-encrypted**, then 302s to `/settings?notion=connected|error`
  - Push: `POST /integrations/notion/push/{project_id}` builds the artifact context (ownership-checked → 404), renders blocks, creates the page; remembers `parent_page_id` in the integration config. `GET /integrations/notion/pages` powers the parent-page picker
  - **Graceful when unconfigured**: with no `NOTION_*` env, `is_configured()` is False → `/authorize` 503s and the Settings card shows "Not available yet". Nothing breaks
  - Frontend: `components/integrations/NotionConnectCard.tsx` (Settings connect/disconnect + post-OAuth toast) and `NotionPushButton.tsx` (Design Kit parent-page picker; inline modal — no shared Modal component exists)
  - **Live in production (2026-05-31)** — Railway env set: `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI` (= `https://backend-production-9c212.up.railway.app/api/v1/integrations/notion/callback`), plus `INTEGRATION_TOKEN_KEY` (Fernet key for token encryption — **never rotate it** or stored tokens become unreadable). A **public** integration is registered at notion.so/my-integrations. OAuth `state` signing falls back to `CLERK_SECRET_KEY`, so **no `SHARE_ACCESS_SECRET` is needed**. OAuth **connect** verified live; end-to-end **push** (Design Kit → Notion page) pending final confirmation
- Other providers: unconnected ones return `status: "coming_soon"`; OAuth/Fernet infrastructure is shared
- Endpoints: `GET /integrations`, `POST /integrations`, `PATCH /integrations/{id}`, `DELETE /integrations/{id}`, `GET /integrations/providers`, plus the 4 Notion routes above
- DB: `external_integrations` table (migration 016) — `access_token`/`refresh_token` (Fernet-encrypted), `config` (JSONB)

### 25. Admin Dashboard
- Hidden `/admin` route gated by `users.is_admin`; non-admins see a polite access-denied panel
- Sidebar shows "Admin" link with 🛡 shield icon only when `user.is_admin === true`
- Two tabs: **Users** (paginated, searchable user table) and **Audit Log**
- User drawer (opens on row click): identity + Stripe/Clerk IDs, plan selector (free/basic/pro), usage counts, entitlement overrides editor (Inherit / Unlimited / Custom per limit key), grant/revoke admin toggle
- **Entitlement overrides** live in `users.entitlement_overrides` (JSONB); `entitlement_service.get_limits()` merges them over plan defaults — any key present in overrides wins, `null` means unlimited for that key
- **Audit log** (`admin_audit_log` table) is append-only — records `admin_user_id`, `action`, `target_user_id`, `details` (before/after JSON), `created_at`
- Audit-logged actions: `plan_changed`, `plan_unchanged`, `overrides_updated`, `admin_granted`, `admin_revoked`
- Self-revoke of admin status blocked at the API layer to prevent lockout
- Backend: `app/routers/admin.py` (with `require_admin` dep), `app/services/audit_service.py`, `app/schemas/admin.py`
- Frontend: `pages/Admin.tsx`, `components/admin/AdminUserTable.tsx`, `components/admin/AdminUserDrawer.tsx`, `components/admin/AdminAuditList.tsx`, `stores/adminStore.ts`
- Endpoints: `GET /admin/users`, `GET /admin/users/{id}`, `PATCH /admin/users/{id}/plan`, `PATCH /admin/users/{id}/overrides`, `PATCH /admin/users/{id}/admin`, `GET /admin/audit-log`
- **First admin bootstrap:** `UPDATE users SET is_admin = TRUE WHERE id = '<id from /auth/me>';` — always use the `id` returned by `/auth/me` (orphan duplicate user rows from old Clerk webhook races can exist; the `/auth/me` id is the canonical row)
- DB: migrations 027 (`is_admin` + `entitlement_overrides`), 028 (`admin_audit_log`)

### 26. Step-by-Step Guided Tour (linear onboarding)
- A **linear, re-openable walkthrough** distinct from the ambient hints (#15) — teaches a first-timer how Ide/AI works end to end (idea → discovery → design kit → prompts → export).
- Themed glass-card overlay (`GuidedTour.tsx`): 7 steps, progress dots, Back/Skip/Next, keyboard nav (←/→/Esc), optional per-step deep-links, finish CTA → `/home`.
- **Floating "?" launcher** (`HelpButton.tsx`) fixed top-right, mounted globally for signed-in users in `App.tsx` (gated on `isSignedIn`). Re-opens the tour any time.
- **Auto-launches once for NEW signups only** (accounts ≤ 7 days old, judged from `authStore.user.created_at`; HelpButton self-hydrates authStore on pages without a Sidebar). Existing users are marked `autoLaunched` silently — no overlay — and keep the "?" launcher + Settings replay. _(Changed 2026-06-10; was everyone-once.)_
- Settings → "Replay Walkthrough" reopens it; "Reset Tutorial" now clears BOTH this tour and the ambient hints.
- Store: `frontend/src/stores/walkthroughStore.ts` (Zustand + persist; only durable flags `completedTour`/`autoLaunched` persist — live `isOpen`/`currentStep` never persist, so a refresh never reopens mid-session). localStorage key `ideai-walkthrough`. Content: `frontend/src/components/tutorial/tourSteps.ts`.
- **Frontend-only** — no backend, no migration.

### 27. Blog (public pages + admin CMS) — conversion funnel
- **Public, SEO-optimized blog** at `/blog` (index) and `/blog/:slug` (post) — standalone public pages (no auth, no app shell), built as a conversion funnel: tutorials/tips with a "Try Ide/AI free" CTA on every page.
- **Admin CMS** in the Admin dashboard (new "Blog" tab): create/edit/publish/delete with live Markdown preview, slug auto-derivation, tags, cover image, excerpt, draft↔publish toggle (`components/admin/AdminBlogManager.tsx`).
- Markdown via **react-markdown + remark-gfm** (raw HTML disabled = XSS-safe for admin-authored content); prose styled by a `.blog-content` block in `styles/globals.css` (no typography plugin). Body headings start at `##` (the post title is the page H1).
- **SEO/GEO:** per-page `react-helmet-async` title/description/canonical/OG/Twitter + JSON-LD (`Blog`/`BlogPosting` + `BreadcrumbList`); `/blog` added to `sitemap.xml`; "Blog" link added to the Landing nav + footer (internal links). Client-rendered (Googlebot renders JS); **per-post build-time prerender is a documented fast-follow** (see Known Issues #6).
- **Backend** (`app/routers/blog.py`, prefix `/blog`): public `GET /blog/posts` (published only, newest first) + `GET /blog/posts/{slug}` (+1 view); admin-only (`require_admin`, audit-logged) `GET/POST /blog/admin/posts`, `GET/PATCH/DELETE /blog/admin/posts/{id}`. Audit actions: `blog_post_created`, `blog_post_updated`, `blog_post_deleted`. View/create/update routes `await db.refresh(post)` after flush to load server-default timestamps before serialization (avoids async-lazy-load `MissingGreenlet`).
- Model `app/models/blog_post.py` (`blog_posts`, migration 033): title, slug (unique), excerpt, body (Markdown), cover_image_url, tags (JSONB), author_name, published, published_at, created_by, view_count, timestamps. Schemas `app/schemas/blog.py`.
- Frontend: `pages/Blog.tsx`, `pages/BlogPost.tsx`, `components/blog/BlogChrome.tsx`, `lib/blogApi.ts`, `lib/blogFormat.ts`, `types/blog.ts`.

---

