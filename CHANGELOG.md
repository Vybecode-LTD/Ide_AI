# Changelog

All notable changes to Ide/AI and its documentation. Format based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/). Doc versioning follows [DOC_VERSIONING.md](DOC_VERSIONING.md).

## [Unreleased]

### Documentation governance — Claude-Kit reconciled to the root-level system (2026-05-30)

### Changed
- **CLAUDE.md v2.12.0** — added a "Doc system scope" override under Documentation Discipline: [DOC_VERSIONING.md](DOC_VERSIONING.md) (root-level docs, SemVer **per doc**, one root CHANGELOG, Stop hook) is the binding convention. The generic Claude-Kit `session-orchestrator` model — a `docs/` managed-doc tree (`docs/BUGS.md`, `docs/HANDOFF.md`, `docs/AUDIT-LOG.md`, …), a single shared version number, and `initialize project docs` — is explicitly **overridden and must not be installed**. Includes a generic-doc → Ide/AI-doc mapping table.
- **DOCUMENTATION_MANAGER.md** (project-local kit directive) — reconciled to this project so it can't mislead a future session: added a PROJECT OVERRIDE banner, remapped the Document Registry to the real root-level docs, replaced the YAML header standard with the one-line frontmatter, overrode the single-shared-version rule with SemVer-per-doc, disabled `docs/`-tree / `initialize project docs` creation, and added a `docs/…` → root-doc name-mapping note covering every downstream reference.

### Notes
- The `session-orchestrator` skill and its 8 subagents stay **globally** installed (`~/.claude/skills` + `~/.claude/agents`) — nothing was moved to the project. The generic directive copies under `Development/` are unchanged and still serve other projects.



### Added
- **GitHub Actions CI pipeline** (`.github/workflows/test-pipeline.yml`) — auto-detects Python/React/C++/.NET stacks, runs lint + tests + security scanning (Gitleaks + CodeQL), deploy gate.
- **OG image source** (`frontend/public/og-image.psd`) — 1200×630 PSD, needs export to PNG.

### Changed
- **CLAUDE.md v2.11.0** — 3 doc-drift fixes: added `admin_audit_log.py` model, expanded types/ listing (4→8 files), corrected module count (47→40).
- **CONTEXT_HANDOFF.md v3.9.0** — updated for doc reconciliation session.
- **TODO.md v3.8.0** — cleaned stale P0 items, added og-image export task.
- **ROADMAP.md v2.4.0** — reconciled Recently Shipped (added phases 5-6, production bugs, alignment audit, security fixes, CI), fixed test counts (91→229), module count (47→40), marked done items, resolved open product question #6.

### Codebase alignment audit — v2 artifact bridge + billing + DesignKit actions (2026-05-27)

### Added
- **Artifact context service** (`backend/app/services/artifact_context_service.py`) — unified bridge between v1 (DesignSheet) and v2 (module_responses) data sources. All downstream consumers (exports, blocks, pipeline, market, sprint) now use `build_artifact_context()` for both flow versions.
- **v2 export support** — `build_export_context_from_artifact()` maps the artifact context to the same template-ready dict shape used by v1. All 5 generators (MD, TXT, PDF, DOCX, ZIP) accept a `context=` keyword arg so v2 projects produce complete exports.
- **v2 block generation** — Extracted shared Claude-call logic into `_generate_blocks_from_prompt_context()`. New `generate_blocks_from_context()` accepts artifact context for v2 projects.
- **v2 pipeline recommendations** — `recommend_pipeline()` accepts `artifact_ctx=` keyword arg; v2 reads problem/audience/platform from module responses.
- **v2 market analysis** — `build_context_from_artifact()` produces the same shape as `build_sheet_context()`. Market generator auto-detects v2 via `project.flow_version`.
- **DesignKit action cards** — `MODULE_ACTIONS` map in `DesignKit.tsx` links modules (blocks, pipeline, prompts, market, sprint, pitch, exports) to their downstream routes with "Open X →" buttons.
- **Stripe subscription lifecycle columns** — Migration 032 adds `stripe_subscription_id`, `subscription_status`, `subscription_price_id`, `subscription_current_period_end` to users table.
- **`authFetch` helper** (`frontend/src/lib/authFetch.ts`) — centralized auth-aware fetch wrapper for raw fetch/SSE calls.
- **Backend dev dependencies** — `[project.optional-dependencies] dev` section in `pyproject.toml` (pytest, pytest-asyncio, aiosqlite, httpx).

### Changed
- **Stripe checkout** now reuses existing `stripe_customer_id` to avoid duplicate customers.
- **Stripe webhook** persists full subscription lifecycle: `checkout.session.completed` stores subscription ID + status + price + period end; `customer.subscription.updated/deleted` updates all 4 columns. Recognizes `trialing` as active.
- **Sharing ratings** — `author_name` defaults to `"Anonymous"` (was required); response returns both old (`count`/`average`) and new (`total_ratings`/`average_score`) keys.
- **Pathway detection** now requires authentication (`get_current_user` dependency added).
- **Prompt rewrite** now requires `prompt_packages` entitlement gate.
- **Module write endpoints** (`respond`, `skip`, `update_responses`, `refresh_output`) validate pathway membership via centralized `_ensure_module_in_project_pathway()` helper.
- **`inboxStore`** throws on missing auth token instead of silently returning.
- **`SprintPlanner.tsx`** uses `authFetch` instead of manual token injection.
- **`docker-compose.yml`** frontend service no longer overrides Caddy image with `npm run dev`.
- **`DEPLOYMENT_RAILWAY.md`** rewritten for actual 2-service topology (no reverse proxy).

### Fixed
- **v2 exports producing empty output** — exports, blocks, pipeline, market, sprint now read from module_responses via artifact context service instead of only from design_sheets.
- **Nested f-string syntax error** in export fallback markdown footer.
- **FeedbackPanel reading wrong response keys** — now reads both `average_score`/`total_ratings` and `average`/`count`.

### Security
- **SAST-H2 fixed**: OpenAPI docs (`/api/docs`, `/api/redoc`, `/api/openapi.json`) now disabled when `ENVIRONMENT=production`.
- **SAST-M1 fixed**: Stripe error responses no longer leak internal details — generic "Payment provider error" message returned to client; raw error logged server-side.
- **SAST-M2 fixed**: `Content-Security-Policy` header added to frontend Caddyfile — allows Clerk, Stripe, GA4, Cloudflare Turnstile; blocks everything else.

### Module completion enforcement + brandmark + codebase audit (2026-05-27)

### Fixed
- **Module sessions never completing** — AI kept asking questions past the configured limit (3 for lite, 10 for deep) because prompt had no enforcement. Added 3-layer fix: (1) `build_module_system_prompt` now receives `questions_asked` count and injects escalating warnings (count awareness → penultimate "LAST question" → CRITICAL "MUST NOT ask"), (2) Output Rules section states the HARD LIMIT explicitly, (3) backend force-complete backstop in `/respond` — if `new_question_count >= max_q` and AI didn't emit `[MODULE_COMPLETE]`, the backend forces completion. Also fixed `/start` endpoint to use `_question_range()` instead of hardcoded `10 if deep else 3` for `total_questions`.
- **`[MODULE_COMPLETE]` marker visible in chat** — Frontend now strips `[MODULE_COMPLETE]` from displayed messages alongside the existing `[CHIPS:]` stripping.

### Changed
- **Brandmark replacement** — Replaced the wide wordmark logo with a square brandmark (`brandmark.png`) across the entire app: Sidebar (desktop + mobile), Landing page (nav, hero, footer), favicon, and apple-touch-icon. All sizing updated from width-based (`w-[200px]`) to height/width pairs with "Ide/AI" text rendered alongside.

### Added
- **31 module completion regression tests** — New `test_module_completion.py` with 6 test classes: `_question_range` mapping (3), `is_module_complete` marker detection (5), `count_questions_asked` accuracy (4), prompt question-count injection at all stages (10), force-complete integration logic (4), prompt content preservation (5).

### Security (orchestrator findings — 3 remaining)
- **SAST-H1** (open): No rate limiting on sharing endpoints — anonymous users can spam. Needs `slowapi` or similar.
- **SAST-M3** (by design): CORS defaults to `localhost:5173` in dev; production uses `CORS_ORIGINS` env var.
- **DEP-H1** (upstream): `js-cookie` CVE — transitive dependency from `@clerk/shared`, cannot be upgraded independently.

### Privacy Policy and Terms of Service pages (2026-05-26)

### Added
- **`/privacy` route** — Full Privacy Policy page (`PrivacyPolicy.tsx`) styled in the Ide/AI dark glassmorphism design system. Covers data collection, AI processing (Anthropic), subprocessors (Clerk/Stripe/Anthropic/Resend/Railway/Google), GDPR rights, retention, and a prominent callout stating Ide/AI never accesses the user's computer or local files. Company: VybeCode LTD, governing law: England and Wales.
- **`/terms` route** — Full Terms of Service page (`TermsOfService.tsx`) with Stripe billing/cancellation terms, device access and file operations section (export/import of `.ideai` files + integration actions only), acceptable use, liability cap (greater of 12-month fees or £100 GBP), and governing law (England and Wales).
- **Footer links** in `Landing.tsx` — "Privacy Policy" and "Terms" links added to the footer nav row.
- Both pages registered as public routes in `App.tsx` (no auth required).

### Add Google Analytics 4 (2026-05-26)

### Added
- **GA4 snippet** in `index.html` — `gtag.js` for measurement ID `G-ZXSEV1H9X6`. Loads async so it never blocks render.

### SEO round 2 — compression, no-cache, og:locale, WebSite schema (2026-05-26)

### Added
- **Caddy `encode zstd gzip`** — all responses now compressed; cuts JS/CSS/HTML transfer sizes 60–80%.
- **`Cache-Control: no-cache, no-store, must-revalidate`** on all non-asset routes — SPA shell is never browser-cached so Railway deploy updates reach users immediately.
- **`og:locale: en_US`** meta tag in `Landing.tsx` Helmet block.
- **WebSite JSON-LD schema** (`@type: WebSite`) added to `Landing.tsx` alongside existing FAQ and SoftwareApplication schemas.

### SEO overhaul — prerendering, meta tags, structured data (2026-05-25)

### Added
- **Build-time SSR prerendering** — `entry-server.tsx` + `scripts/prerender.mjs` render the landing page to static HTML at build time using React DOM server + `StaticRouter`. The pre-rendered HTML is injected into `dist/index.html` so crawlers and social bots see full content without executing JavaScript. SSR bundle in `dist/server/` is deleted after use.
- **`react-helmet-async`** — Installed and wired via `HelmetProvider` in `main.tsx`. `Landing.tsx` sets dynamic title, meta description, OG tags, Twitter Cards, and canonical URL per route (`/` vs `/pricing`).
- **JSON-LD structured data** — FAQ schema (`FAQPage`) and product schema (`SoftwareApplication` with `Offer` entries for all plans) injected by `Helmet` in `Landing.tsx`. FAQ schema enables Google rich-result accordions directly in SERPs.
- **`robots.txt` + `sitemap.xml`** — Created in `frontend/public/`. Sitemap covers `/` and `/pricing`; robots disallows all authenticated/app routes.
- **`@fontsource/jetbrains-mono`** — Self-hosted JetBrains Mono replaces the Google Fonts CDN request, eliminating a cross-origin DNS round-trip that was blocking the render path.
- **LCP image preload** — `<link rel="preload">` for `brandmark.png` in `index.html`; `fetchPriority="high"` on the hero `<img>` to signal the browser's preload scanner.
- **Caddy: LCP preload `Link` header + `X-Robots-Tag`** — Root path gets an HTTP `Link` preload header for the hero image; added `X-Robots-Tag: index, follow` to security header block.
- **`vite.config.ts` SSR config** — `ssr.noExternal: ['framer-motion', 'react-helmet-async']` ensures these ESM-only packages are bundled for the Node.js prerender environment.

### Changed
- **`package.json` build script** — Extended to `tsc -b && vite build && vite build --ssr ... && node scripts/prerender.mjs`.
- **Hero description copy** — Replaced "the first AI platform" (unverifiable claim) with "the AI concept development platform"; added "Turn any idea into a complete design kit in under 15 minutes" for keyword density and urgency.
- **Hero brandmark `alt` text** — Updated to `"Ide/AI — AI concept development platform"` for keyword-aware alt text.

### Note
- **OG image still needed** — `og-image.png` (1200×630) referenced in meta tags but not yet in `frontend/public/`. Create and drop it there; social shares will show a blank card until it exists.

### Proceed button + Design Kit mobile layout (2026-05-25)

### Fixed
- **Proceed button falsely enabled at 85%** — `compute_field_summary()` counted fields as "filled" based on key existence alone; empty strings, `None`, empty lists, and empty dicts all inflated the count. Added `_has_value()` validator that requires meaningful non-empty content. Additionally, the proceed button now gates on `overall_percent >= 100` (matching the visible header badge) instead of required-only percentage, eliminating the confusing mismatch.
- **Design Kit "Continue Discovery" button cut off on mobile** — Header buttons were in a non-wrapping `flex` row that overflowed on narrow screens. Refactored to stack vertically on mobile with a dedicated sticky bottom bar for the primary "Continue Discovery" CTA. Added bottom padding to prevent content occlusion.

### Added
- **8 regression tests for `compute_field_summary`** — Validates that empty strings, None, empty lists, empty dicts, and whitespace-only values do NOT count as "filled"; genuine values DO count; missing keys and absent DB rows handled correctly.

### Fix PDF transcript export + safe filenames (2026-05-25)

### Fixed
- **PDF transcript export "Network Error"** — Project names containing Unicode characters (em-dashes, quotes, slashes, emoji) were passed unsanitized into `Content-Disposition` headers, corrupting the HTTP response and causing mobile browsers to report a network error. Introduced `safe_filename_slug()` utility that strips everything except `[a-z0-9-]`.
- **All 7 export endpoints hardened** — Applied `safe_filename_slug()` across discovery transcript, design kit export, prompt package, market analysis, library `.ideai`, sprint CSV, and sharing CSV exports.

### Added
- **`export_service.safe_filename_slug()`** — Shared ASCII-safe slug generator for `Content-Disposition` filenames. Replaces 7 separate inline `name.lower().replace(" ", "-")[:30]` patterns.
- **Try/except wrapper on PDF generation** — Transcript PDF endpoint now returns a proper 500 JSON error instead of crashing the response stream.

### Chip relevance overhaul (2026-05-25)

### Fixed
- **Quick-reply chips showed generic "Yes exactly" / "Not quite" responses** — Replaced the keyword-bucket fallback system with an AI-powered chip generator that asks Claude to produce 3 contextual answer options matching the actual question asked. Generic chips are now impossible.
- **All 4 prompt variants** (v1 system, v1 greeting, v2 system, v2 greeting) now include a FORBIDDEN list of banned chip texts ("Yes exactly", "Not quite", "Tell me more", etc.) so the AI avoids generating them in the first place.

### Added
- **`__type_your_answer__` sentinel chip** — When a question is too open-ended for preset answers, the backend sends this sentinel. The frontend renders a distinct amber "Type your answer below" indicator (non-clickable, `role=status`) instead of useless generic options.
- **Generic-chip filter** — Strategy 1 (parse `[CHIPS:]` tag) now validates extracted chips against a blocklist of known generic responses and falls through to AI generation if all chips are generic.

### Production bug fixes — mobile overflow, proceed gate, extraction (2026-05-25)

### Fixed
- **Mobile horizontal overflow in Discovery** — AI partner messages and quick-reply chips overflowed the viewport on mobile. Added `min-w-0` to flex containers in Discovery.tsx and `overflow-x-hidden` to ChatThread.tsx and QuickChips.tsx.
- **Proceed button activated prematurely** — "Proceed to Design Kit" was clickable at any completion percentage. Now disabled until 100% of required fields are filled; shows muted `N% complete` badge when below 100%.
- **Field extraction stalled at ~85%** — Two root causes: (1) extraction prompt received the entire conversation history, diluting signal for recent answers; (2) extraction rules were too conservative, skipping implied answers. Fixed by windowing extraction to last 8 messages (`_EXTRACTION_WINDOW`) and making extraction aggressive (synthesize answers from context, extract partial matches).

### Changed
- **Discovery system prompt** — Added rules "NAME THE TARGET" (phrase questions to map directly to fields) and "ACKNOWLEDGE AND FILL" (move to next field immediately after acknowledgment). Strengthened vague-answer handling to suggest concrete answers for confirmation.
- **Extraction prompt** — Now includes a "STILL MISSING" section listing unfilled fields explicitly. Rules rewritten to extract aggressively and synthesize reasonable answers from context.

### Admin tests + toast cleanup (2026-05-24)

### Added
- **27 admin endpoint integration tests** in `test_admin.py` — `require_admin` 403 gate (3 tests), user list pagination/search/filter (4), user detail + 404 (2), plan update + audit log creation (4), entitlement override merge into effective limits (4), admin flag grant/revoke + self-revoke block (5), audit log listing with filters + email resolution (5).
- **`admin_audit_log` model import** in `conftest.py` so the test harness creates the table.

### Changed
- **`Home.tsx`** — replaced `createError` useState + inline error banner with `toast.error(extractError(...))`.
- **`SprintPlanner.tsx`** — removed `errorMessage` useState + inline error banner, unified on `toast.error(...)`.
- **TODO.md → 3.5.2**, **CONTEXT_HANDOFF.md → 3.5.2**, **CLAUDE.md → 2.9.2** (PATCH bumps — tests + cleanup).

### Phase 6 audit fix + regression hardening (2026-05-24)

### Fixed
- **Library `latest_session_sq` picked up scoped sessions** — Added `scope_module_ids.is_(None)` filter to the DISTINCT ON subquery in `library.py` so mini-Discovery sessions don't override main-flow status in the Library view.
- **Orphan cleanup abandoned scoped sessions** — Added `scope_module_ids.is_(None)` filter to the orphan-cleanup query in `get_latest_active_session_for_project` so freshly-created scoped sessions aren't retired as orphans.
- **No validation on `scope_module_ids` entries** — `POST /discovery/start` now validates that all scope module IDs exist in the project's `ModulePathway.modules`. Returns 400 for invalid IDs and for scoped sessions on v1 projects.
- **Empty `scope_module_ids=[]` treated as scoped** — Added Pydantic `field_validator` on `SessionCreate` to normalize empty lists to `None` (unscoped resume).
- **Frontend `scopeModuleIds` not in `useEffect` deps** — Added `scopeParam` to the bootstrap effect's dependency array in Discovery.tsx so scope changes trigger re-initialization.
- **DesignKit unfilled check only tested key existence** — `unfilledModules` filter now checks for `undefined`, `null`, and empty string values, not just missing keys.
- **Migration 031 docstring** — Referenced "discovery_sessions" table but actual table is "sessions". Corrected.
- **Model type annotation** — `scope_module_ids` was `Mapped[list | None]` (unparameterized); now `Mapped[list[str] | None]`.

### Added
- **4 audit-driven tests** in `TestScopedSessions`: empty scope normalization, nonexistent module ID rejection, v1 scoped session rejection, multi-module scope with field-summary filtering.
- **6 regression tests** in `TestAuditFixRegressions` (integration): library excludes scoped sessions, main-flow resume survives multiple scoped sessions, v1 discovery unaffected by validation, mixed valid/invalid scope IDs rejected, null scope in normal responses, full-module field-summary on main sessions.
- **6 service-layer regression tests** in `TestSessionResumeRegression`: basic resume, scoped always-create, scoped-doesn't-pollute-main, get-latest-ignores-scoped, orphan-cleanup-skips-scoped, force-new-alongside-scoped.

### Phase 6 mini-Discovery scoped sessions (2026-05-24)

### Added
- **Migration 031** — `scope_module_ids` JSONB column on `discovery_sessions`. When non-null, the session is scoped to only those module IDs (mini-Discovery for newly-added modules).
- **Scoped session create** — `POST /discovery/start` accepts `scope_module_ids` in the body. Scoped sessions always create new (never resume); main-flow resume excludes scoped sessions.
- **Scoped init/message/field-summary** — `/discovery/{session_id}/init`, `/message`, `/field-summary` all filter decorated modules to the session's scope when set.
- **"Continue Discovery" button** — DesignKit header shows a "Continue Discovery (N)" button when modules have unfilled required fields. Navigates to `/discovery/:projectId?scope=mod1,mod2,...`.
- **Discovery scoped mode UI** — TopBar shows "Continue Discovery" title + "N modules scoped" subtitle. Proceed button reads "Back to Design Kit" instead of "Proceed to Design Kit".
- **4 integration tests** in `TestScopedSessions`: scoped session creation, main-flow isolation, no resume into existing scoped sessions, field-summary scope filtering.

### Fixed
- **SQLite JSON NULL gotcha** — Explicitly passing `None` to a SQLAlchemy JSON column on SQLite stores JSON null (not SQL NULL), breaking `IS NULL` queries. Fixed `create_session` to omit `scope_module_ids` from the constructor when it's `None`.

### Phase 5 Design Kit + Vitest scaffold (2026-05-24)

### Added
- **`frontend/src/pages/DesignKit.tsx`** — Full Design Kit page with ModuleCard components, FieldEditor (type-aware: text/longtext/list-as-chips/dict-as-key-value), FieldDisplay, grouped by module group, overall progress bar, Export button. Route at `/design-kit/:projectId`.
- **`backend/app/routers/module_pathway.py` — `GET /{project_id}/design-kit`** endpoint returning decorated modules + field schemas + current response values.
- **`backend/app/routers/modules.py` — `PATCH /{project_id}/{module_id}/responses`** partial-update endpoint with schema validation + `_coerce_field_value` + unknown-key rejection.
- **Vitest scaffold** — `vite.config.ts` test config, `@testing-library/react` + `@testing-library/jest-dom`, setup file.
- **31 frontend tests** across 4 files: `extractError.test.ts` (14), `inboxStore.test.ts` (5), `useSSE.test.ts` (6), `ProgressPanel.test.tsx` (6).
- **5 backend integration tests** in `TestDesignKitEndpoint` class covering GET design-kit + PATCH responses (happy path, unknown key rejection, non-v2 project rejection, cross-user 404).
- **Library resume routing** for v2 — completed sessions or pathways route to `/design-kit/{pid}`.
- **Refresh output for `has_output` modules** — `POST /modules/{project_id}/{module_id}/refresh-output` generates a formatted document from field values via AI. Frontend: "Generate Output" / "Regenerate" buttons on DesignKit module cards. Output stored in `responses.__generated_output`. 3 integration tests.
- **Add Modules picker** — "Add Modules" button in DesignKit header opens a category-filtered modal showing all library modules not yet in the pathway. `POST /projects/{project_id}/pathway/modules` appends selected IDs with dedup + unknown-ID validation. 3 integration tests.

### Changed
- **Discovery.tsx** — v2 Proceed button now routes to `/design-kit/${projectId}` instead of `/exports/${id}`.
- **`_compute_resume_path`** in `library.py` — v2 projects with completed session or pathway status "complete" resume to `/design-kit/{pid}`.
- **CLAUDE.md → 2.8.0**, **CONTEXT_HANDOFF.md → 3.4.0**, **TODO.md → 3.4.0** (MINOR bumps — new feature).

### Post-push doc refresh (2026-05-23, end-of-session)

All 5 v2-overhaul + doc commits (`b26837a` `ff212f3` `57aa9d3` `f8d3165` `585cb7d`) pushed to `origin/main`. Railway auto-deploy triggered for both backend + frontend services.

### Changed
- **TODO.md P0 block** — first item (`git push origin main`) marked DONE. Remaining P0 items adjusted: verify Railway deploy succeeded → 5-min smoke test → rotate 3 exposed webhook secrets.
- **CONTEXT_HANDOFF.md P0 block** — push marked done with ✅, smoke + secret-rotation items kept as ⚠️.
- **MEMORY.md "Most recent session signature"** — HEAD updated, "Unpushed: 4 commits" replaced with "All pushed to GitHub and have triggered Railway auto-deploy". P0 Next item simplified to "verify + smoke + rotate".
- **ROADMAP.md "Up Next #0"** — push step marked ✅ DONE, refocused on deploy verification + smoke + secret rotation.
- **CLAUDE.md "Last Completed Task"** — refreshed from the way-stale admin/error-UX/doc-versioning description to reflect the v2 overhaul + audit closure + integration tests + doc unification work that actually shipped this session. Lists all 5 commits.
- **CLAUDE.md → 2.7.4**, **CONTEXT_HANDOFF.md → 3.3.4**, **TODO.md → 3.3.3** (PATCH bumps — post-push state reflection, no feature change).

### Doc unification pass — close drift + cross-reference gaps

Follow-up to the previous doc-lockdown commit. Audit caught two real-staleness issues that would have actively misled the next session, plus 4 cross-reference gaps.

### Fixed
- **`MEMORY.md` Most recent session signature** was severely stale — claimed HEAD was `fb1f1b8` (4+ commits behind reality, pre-Phase-1) and listed "Next: Railway env-var setup" as if that was still pending (long done). Since MEMORY.md is read 3rd in CLAUDE.md's Session Recovery order (right after CLAUDE.md + DOC_VERSIONING), this would have given the next Claude session an obsolete mental model from the start. Refreshed to reflect actual HEAD `f8d3165`, 4 unpushed commits (highlighting the H1 prod-bug fix in `57aa9d3`), and Phase 5 as next.
- **`ROADMAP.md` Recently Shipped + Up Next** was partially stale — said "Phases 1-2 shipped today" and listed Phases 3-6 as remaining, but actually Phases 1-4 + audit closure are all shipped. Bumped to 2.2.0. Recently Shipped now covers all 9 v2-overhaul commits; Up Next opens with P0 (push + smoke + secrets), then Phases 5-6, then Vitest scaffold, then Notion integration.
- **Phase 5 list drift** between TODO.md (7 items) and CONTEXT_HANDOFF.md (6 items) — CONTEXT was missing the Library resume routing item. Re-synced; CONTEXT now points readers to TODO.md as canonical.

### Added
- **Cross-references in `TODO.md` frontmatter** — explicitly points readers to ROADMAP.md, CONTEXT_HANDOFF.md (incl. the Regression Test Matrix), and MEMORY.md. Closes the gap where TODO.md never mentioned CONTEXT_HANDOFF.
- **Cross-reference in `TODO.md` Test coverage section** — "before adding tests, check the Regression Test Matrix in CONTEXT_HANDOFF.md (91 tests across 4 files)". Marks the Discovery v2 endpoint integration tests TODO as DONE (commit `57aa9d3`). Adds new SSE-streaming-tests TODO item.
- **Cross-references in `MEMORY.md` frontmatter** — explicitly points to CONTEXT_HANDOFF.md, TODO.md, CHANGELOG.md.
- **Cross-references in `ROADMAP.md` frontmatter** — now includes CONTEXT_HANDOFF.md alongside the existing TODO.md and CHANGELOG.md.
- **Deprecation notes on `MODULAR_PATHWAY_SPEC.md` + `MODULAR_PATHWAY_IMPLEMENTATION_PROMPT.md`** — these were pre-v2 specs with no "superseded" indicator. New banner at the top explains they describe the v1 per-module-session flow and points readers to CLAUDE.md feature 5 + the discovery-v2-architecture memory for the current architecture.

### Changed
- **CLAUDE.md → 2.7.3** (PATCH — doc reorganization, no feature change). **CONTEXT_HANDOFF.md → 3.3.3**. **TODO.md → 3.3.2**. **ROADMAP.md → 2.2.0** (MINOR — new content covering the v2 overhaul + restructured Up Next queue).

### Doc lockdown for fresh-session pickup

Closed four gaps in the handoff docs identified when preparing to start a new Claude session — work that was real but only lived in chat history wasn't durable.

### Changed
- **Project memory `discovery-v2-architecture.md`** rewritten to reflect Phases 1-4 + audit closure + integration tests all shipped. Previous version said "Phase 4 NEXT" which would have given the next session wrong context on auto-load.
- **`TODO.md`** — added a new `🔴 P0 — DO TODAY` block at the top covering the 3 unpushed commits + smoke test + webhook secret rotation. Until those commits are pushed the H1 greenlet fix is dormant in production.
- **`TODO.md` Phase 5 section** — added a **Recommended sequencing** subsection explaining Vitest scaffold should land BEFORE Phase 5 polish (Refresh / Add Modules), and that every new endpoint should ship with a matching `test_discovery_v2_integration.py` test before declaring done. Numbered the 7 items for easier reference.
- **`CONTEXT_HANDOFF.md`** — added a `🔴 P0 — Do today` block under What Still Needs Your Action (mirrors TODO P0). Added recommended-sequencing pointer to Phase 5 section. Appended a **Regression Test Matrix** table mapping each major code path to its protecting test file + count, with explicit Known Gaps callout (PG-only upsert, SSE streaming, frontend behavior, admin endpoints).
- **CLAUDE.md → 2.7.2** (PATCH — doc reorganization, no feature change). **CONTEXT_HANDOFF.md → 3.3.2**, **TODO.md → 3.3.1**.

### Phase 4 HTTP-level integration tests + H1 prod-bug fix

After the audit closure, added FastAPI TestClient-based integration tests covering the HTTP routes the service-layer tests in `test_discovery_v2.py` couldn't reach. The new suite immediately caught a real production bug in the H1 fix.

### Fixed
- **`projects.py` greenlet-during-serialization bug.** The H1 downgrade (`project.flow_version = "v1"; await db.flush()`) was implicitly expiring `updated_at` (server_default/onupdate column). FastAPI's response-serialization then tried to lazy-load it outside the greenlet context, raising `MissingGreenlet`. Fix: `await db.refresh(project)` after the downgrade so all server-default columns are populated before serialization. Every H1-downgraded project would have hit this in production (any POST /projects without primary_category, or with a failing assembly). Caught by `test_downgrades_to_v1_when_no_primary_category` in the new integration suite.

### Added
- **`backend/tests/test_discovery_v2_integration.py`** — 15 tests using FastAPI TestClient with dependency overrides for `get_db` + `get_current_user`. Covers:
  - **TestCreateProjectH1** (5 tests): v2-with-pathway happy path, H1 downgrade on no-category, H1 downgrade on empty assembly (monkeypatched), H1 downgrade on assembly exception (monkeypatched), Phase-2-hotfix invariant that `module_pathways.modules` is `list[str]`.
  - **TestFieldSummaryEndpoint** (4 tests): 200 + correct shape for v2, 409 for v1, 404 for nonexistent session, 404 for cross-user session (security check).
  - **TestTemplateFlowVersion** (1 test): Phase 3 hotfix invariant that template-created projects are `flow_version='v1'`.
  - **TestLibraryResumeRouting** (2 tests): exhaustive matrix proving v2 always routes to `/discovery`, plus v1 routing unchanged across all 5 legacy states.
  - **TestDiscoveryStartV2** (2 tests): session creation with partner-style propagation, cross-user 404 isolation.
  - **TestProjectReadShape** (1 test): asserts every field the Phase 4 frontend `Project` type expects is present in the response.

### Coverage summary
- **Backend tests: 91 total, all passing** (41 existing + 35 unit + 15 integration).
- Phase 1-4 + audit closure now has HTTP-level regression coverage for: H1 (4 cases), M6 endpoint (4 cases), Phase 3 hotfix (template v1 flag), `_compute_resume_path` (exhaustive matrix), discovery start ownership check, ProjectRead shape, pathway-shape invariant. PostgreSQL ON CONFLICT upsert is still out of scope (SQLite harness). SSE streaming endpoints are not exercised — that would require mocking the AsyncAnthropic streaming client.

### Changed
- **CLAUDE.md → 2.7.1** (PATCH — real bug fix in `projects.py` + new test file, no documented-feature change).

### Phase 4 audit closure (previous commit)

End-of-Phase-4 internal audit identified 2 HIGH, 8 MEDIUM, 5 LOW findings across the v2 code paths. All actionable items resolved in a single sweep with regression testing between each phase. 76/76 backend tests now pass (35 new v2 tests + 41 existing), TypeScript build clean.

### Fixed
- **H1 — v2 project stranded when up-front assembly skipped.** [projects.py](backend/app/routers/projects.py) now downgrades `flow_version` to `'v1'` when no pathway row is created (no `primary_category`, empty assembly, or assembly exception). Previously these orphan v2 projects rendered ProgressPanel forever empty + no Proceed button.
- **H2 — `PathwayExecute.tsx` missing v2 redirect.** Defense-in-depth gap closed. v2 users who deep-link to `/pathway-execute/{pid}` now bounce back to Discovery, matching the existing PathwayReview behavior. Prevents the legacy per-module session from clobbering v2-populated `module_responses`.
- **M8 — Proceed button never appeared for all-optional pathways.** Gate changed from `required_total > 0` to `total_fields > 0` in [Discovery.tsx](frontend/src/pages/Discovery.tsx). Warning chip still only shows when `required_total > 0` AND `required_filled / required_total < 80%`.
- **New defensive check in `apply_extracted_module_fields`** — unknown field keys (compound keys within valid modules but not in the schema) are now logged + rejected instead of silently coerced to text and persisted. Caught by the new test suite.

### Added
- **M6 — `GET /api/v1/discovery/{session_id}/field-summary` endpoint.** Returns the current `compute_field_summary` payload for a v2 session. Frontend `Discovery.tsx` now hydrates the ProgressPanel from this endpoint on mount, closing the resume-mid-session blank-state gap. Returns 409 for v1 projects so the client knows to render the legacy panel.
- **M3 — `build_unified_greeting_prompt`** in `ai_service.py`. v2 projects get a greeting that names the assembled module set + steers toward the first required field's extraction hint. Init handler in `discovery.py` branches on `flow_version`. v1 keeps the legacy `build_greeting_prompt`.
- **M7 — `_coerce_field_value` drop logging** with module/field/declared-type/raw-value context. Surfaces silent extraction drops in Railway logs without affecting UX.
- **M1 — extraction prompt instructs dict fields to return whole object** (existing keys merged with new updates) so the JSONB shallow merge doesn't lose nested keys.
- **`load_decorated_pathway_modules` service helper** in `discovery_service.py` — extracted from the inline decoration logic in the message handler so the new field-summary endpoint can reuse it. Tolerates both list[str] and legacy list[dict] shapes.
- **L5 — `_reset_module_library()` test hook** in `modular_pathway_service.py`. Lets tests force a re-read of the seed file or inject a mock library.
- **I4 — new test file `backend/tests/test_discovery_v2.py`** with 35 tests covering: `_coerce_field_value` (12 cases), `_reset_module_library` (2), `compute_field_summary` (4 DB-backed), `load_decorated_pathway_modules` (4 DB-backed), `apply_extracted_module_fields` (2 — validation logic, not the PG-only upsert), `build_unified_discovery_prompt` (3), `build_unified_greeting_prompt` (3).

### Changed
- **L1 — ProgressPanel "just filled" highlight fades after 8s.** `recentUpdates` state auto-clears via `setTimeout` so the accent doesn't linger between AI turns.
- **L2 / M5 — ProgressPanel expanded set capped at 3 modules** with FIFO eviction. Applies to both auto-expand (on field_update) and manual user clicks. Prevents scroll clutter on long sessions with many module updates.
- **M2 / L3 — Stage UI hidden for v2.** `Discovery.tsx` no longer renders TopBar subtitle (`Stage: greeting`), left StagesStepper, or mobile stage indicator for v2 projects. v2 has no meaningful stage progression; the ProgressPanel carries the equivalent signal.
- **M4 — `loadSheet()` skipped for v2.** Bootstrap effect in `Discovery.tsx` consolidated: project fetched first, `flow_version` known before session start, design-sheet load only runs for v1. Removes the wasted 404 round-trip on v2 session start.
- **CLAUDE.md → 2.7.0** (MINOR — new endpoint + new helper + new test file, all backwards-compatible).

### In progress — Unified Discovery overhaul (Phases 1-4 of 6 shipped)

The discovery → design kit flow is being restructured. Old `v1` projects keep the existing PathwayReview → Execute → per-module sessions path. New `v2` projects (default for all newly created projects) will use a unified Discovery that funnels toward filling fields across an up-front-assembled module pathway, then land directly on a complete Design Kit. See ROADMAP "Up Next" for the full 6-phase plan.

**Phase 4 (this commit) — frontend ProgressPanel + v2-aware Proceed gate + overlay a11y:**
- **`components/discovery/ProgressPanel.tsx`** (new) — module-aware progress meter that replaces `DesignSheetPanel` on the right side of Discovery for v2 projects. Renders overall % header with progressbar role, expandable per-module breakdown showing filled / required-left / optional-left counts, and an accent highlight on fields just-filled by the latest extraction batch. Auto-expands whichever module the AI most recently extracted into.
- **`hooks/useSSE.ts`** — new `onFieldUpdate` callback + exported `FieldUpdate`, `FieldSummary`, `FieldUpdatePayload` types. Parses the `field_update` SSE event emitted by the Phase 2 backend (previously silently dropped). `onSheetUpdate` (v1) and `onFieldUpdate` (v2) coexist; only one fires per AI turn depending on `project.flow_version`.
- **`pages/Discovery.tsx`** branches on `flowVersion`:
  - Fetches `flow_version` from `GET /projects/{id}` on mount and stores it. Falls back to `'v1'` if the project fetch errors so the legacy sheet panel still renders.
  - Right side renders `<ProgressPanel>` for v2, `<DesignSheetPanel>` for v1.
  - Mobile toggle button label switches between "Progress" and "Sheet"; badge shows `overall_percent` (v2) or `confidence_score` (v1).
  - Proceed button gate replaced. v1 unchanged (`sheet.confidence_score >= 70` → `/pathway-review/{id}`). v2 always available once `fieldSummary.required_total > 0`, routes to `/exports/{id}` as the interim Design Kit destination (the Phase 5 `/design-kit/{id}` page swaps the destination in). Warning chip with the live `required_filled / required_total` percentage when below 80%.
- **`pages/Home.tsx` module-preview overlay a11y + mobile (Phase-3-deferred audit items):**
  - Extracted to new `ModulePreviewOverlay` subcomponent with `role="alertdialog"`, `aria-labelledby` on heading, `aria-describedby` on subtitle.
  - Dialog focused on mount; `Escape` key skips the 2.2s wait and navigates immediately. Visible "Skip Esc" hint in the footer.
  - Mobile overflow fix: dialog `max-h-[88vh]`, grid `max-h-[40vh]` on small screens (was `max-h-60` / 240px, which overflowed at <360px viewport).
  - Destination URL captured on the overlay state so the Esc handler can navigate without recomputing it.
- **`types/project.ts`** — added `flow_version: 'v1' | 'v2'` plus `primary_category`, `secondary_category`, `pathway_locked` (all returned by backend `ProjectRead` but missing from the frontend type until now).

Known Phase-4 limitation (intentional, scoped to Phase 5): on resume, the ProgressPanel shows its empty state until the user's next message. The `field_update` event fires after AI replies, not on session-resume. A dedicated `GET /discovery/{id}/field-summary` endpoint to seed the panel on mount is a Phase 5 follow-up — once `/design-kit/{id}` exists, it'll load the summary directly and resume-on-Discovery becomes less common.

- CLAUDE.md → 2.6.0 (MINOR — new user-visible feature: ProgressPanel + v2 Proceed gate + a11y improvements)

**Phase 1 (commit `fb840de`):**
- `projects.flow_version` column (migration 029) — `v2` default, existing rows backfilled to `v1`
- Field schemas on every module in `module_library.seed.json` — 40 modules, 154 total fields (52 required, 102 optional), 6 modules flagged `has_output`
- Up-front pathway assembly at project creation
- New helpers: `get_module_fields`, `get_pathway_field_summary`, `assemble_pathway_from_creation_inputs`

**Phase 3 hotfix (this commit, post 2-agent audit):**
- **`Home.tsx` setTimeout leak fixed** — preview-navigate timer is now stored in a `useRef` and cleared in an unmount effect. Previously the orphan timer could fire after the component unmounted, yanking a user away from wherever they manually navigated to during the 2.2s preview window.
- **`Home.tsx` billing-URL category preservation** — the billing-success cleanup effect now strips only `?billing=success` and preserves all other query params (notably `category`). Previously a user landing on `/home?category=software&billing=success` lost their category selection mid-flow.
- **`templates.py` flow_version='v1'** — template-created projects now explicitly set `flow_version='v1'` (was defaulting to `'v2'` from the column default). Template projects don't run up-front pathway assembly, so being marked v2 would break Library resume routing and PathwayReview redirects. Phase 5 may revisit once `/design-kit` can render template-seeded fields.
- **`library.py:_compute_resume_path` flow_version branch** — v2 projects now always resume to `/discovery/{pid}` (the unified Discovery is their only surface until Phase 5's `/design-kit` ships). v1 routing untouched.
- **`PathwayReview.tsx` v2 redirect** — fetches the project on mount; if `flow_version === 'v2'`, immediately redirects to `/discovery/{projectId}` so v2 users who deep-link or get bounced here don't fall into the legacy review/lock flow which would clobber their up-front-assembled pathway.
- CLAUDE.md → 2.5.1 (PATCH — pure bug fixes, no documented-feature change)

Audit findings deferred to Phase 4 (not blockers for handoff):
- Discovery "Proceed to Design Kit" button still requires `sheet.confidence_score >= 70` (effectively unreachable for v2). Phase 4 ProgressPanel replaces this trigger with a field-completion check.
- DesignSheetPanel on the right side of Discovery still renders for v2 (empty/blank state). Phase 4 swaps it for ProgressPanel.
- Module-preview overlay a11y (`role="status"` vs `role="alertdialog"`) and mobile overflow on tiny viewports.

**Phase 3 (commit `94102cb`) — frontend Home reorder + post-create module preview:**
- Moved `TemplateGrid` directly below the partner-style picker (was below the Submit button) per the v2 UX spec: "partner style with templates below it and optional advanced configuration".
- New `showPreviewAndNavigate(projectId)` flow on the Submit handler: after a v2 project is created, fetch `/projects/{id}/pathway`, then show a glassmorphism overlay listing every module the AI will fill during Discovery, then auto-route to `/discovery/{id}` after 2.2 seconds.
- Overlay is animated (AnimatePresence) with per-module stagger. Falls through to immediate navigation when the pathway endpoint 404s (template projects, v1 projects, or assembly skipped at creation).
- Tolerates both list-of-strings AND list-of-dicts shape from `/projects/{id}/pathway` (legacy data) so the overlay renders cleanly whether migration 030 has run or not.
- Frontend now respects `data.flow_version === 'v2'` returned from POST /projects to decide between the overlay path and the legacy immediate-nav path.
- CLAUDE.md → 2.5.0 (MINOR — new user-visible UX flow).

**Phase 2 hotfix (commit `23f5e7d`):**
- **Migration 030** — three forward-only data fixes:
  1. Backfill `module_pathways.modules` from list[dict] → list[str] for any rows already created on the broken Phase-1 shape
  2. Dedup `module_responses` by (project_id, module_id) keeping the newest row per pair
  3. Add `UNIQUE(project_id, module_id)` on `module_responses` so the race-safe ON CONFLICT upsert can apply field updates without duplicate-row pile-ups
- **`projects.py`** now stores module-id strings only on `module_pathways.modules` (matches `PathwayRead.modules: list[str]` and `modules.py`/PathwayExecute consumers). Empty assembly results no longer create an orphan pathway row.
- **`discovery.py`** now decorates `mp.modules` (strings) into full module entries (with `label`, `description`, `group`, `fields`, `has_output`) at read time by looking up the library definition. Tolerates legacy list[dict] shape too in case migration 030 hasn't run for a given DB.
- **`discovery_service.apply_extracted_module_fields`** rewritten to use PostgreSQL `INSERT ... ON CONFLICT (project_id, module_id) DO UPDATE` with JSONB `||` merge. Concurrent calls from the same project (multi-tab, retry) no longer race.
- **Type coercion** via new `_coerce_field_value(value, field_type)` helper — if the AI returns a string for a list-typed field, it's wrapped; a dict for a list field is values-extracted; a scalar for a dict field is rejected (returns None). Defends against schema-shape drift.
- **SSE serialization safety**: `json.dumps(..., default=str)` on all event payloads in discovery.py — guards against datetime / UUID / Decimal values sneaking in from JSONB columns.
- **CLAUDE.md** → 2.4.1 (PATCH bump — internal robustness, no documented-feature change)

**Phase 2 (commit `8cfc66a`):**
- `ai_service.build_unified_discovery_prompt(...)` — new system prompt builder that exposes ALL assembled modules + their field schemas + already-filled state, and instructs the AI to funnel toward the first unfilled REQUIRED field each turn. Layered with the existing partner-style fragments. Includes the standard CHIPS rules.
- `ai_service.extract_module_fields(messages, modules, current_fields)` — new extractor that returns a JSON dict keyed by `"module_id.field_key"`. Validates returned keys against the schema and drops anything not recognized. Handles markdown-fence-wrapped JSON.
- `discovery_service.get_filled_fields_for_project(...)` — loads current state of `module_responses.responses` grouped by module_id.
- `discovery_service.compute_field_summary(...)` — aggregates total/required/per-module completion counts for the progress meter payload.
- `discovery_service.apply_extracted_module_fields(...)` — writes extracted values into `module_responses` (creates rows on first touch, merges into existing rows otherwise) and returns `(updates_list, summary)` for the SSE event.
- **`/discovery/{id}/message` now branches on `project.flow_version`**:
  - v1 projects: unchanged — design-sheet prompt + sheet_update event
  - v2 projects: unified prompt + field_update event with the per-module summary
- New SSE event type: `field_update` carrying `{updates: [{module_id, field_key, value}], summary: {total_filled, total_fields, required_filled, required_total, overall_percent, per_module: [...]}}`
- Done event still always fires with chips fallback (Phase-pre fix from earlier today carried through).

Phase 5 (Design Kit page at `/design-kit/{id}` with per-module Edit + Refresh affordances) is the next slice. Phase 6 (Additional Discovery for newly-added modules) closes the v2 frontend overhaul.

---

## [2026-05-23] — Discovery SSE Robustness

### Fixed
- **Assistant messages now persist independently from sheet extraction.** Previously, `/discovery/{id}/message` committed the assistant message AND sheet updates in the same transaction at the end of the stream. If the sheet extraction or its commit raised (JSONB serialization, concurrent write, etc.), the entire transaction rolled back — taking the assistant message with it. On resume, users saw only their own messages with the AI side missing. Fix: assistant message gets its own commit immediately after token streaming completes; sheet extraction is a separate transaction with its own rollback.
- **`done` event is now guaranteed to fire**, even when chip generation or JSON serialization fails. The final `yield` is wrapped in try/except with a hardcoded fallback sentinel. If `generate_quick_chips` raises, a 3-item generic chip list is used. This fixes the "chips appeared sometimes, randomly" symptom where the stream silently ended after the last token without emitting `sheet_update` or `done`.
- **Empty chip list from `generate_quick_chips`** now falls back to the 3-item default before being sent (was already happening for most code paths but a single-option `[CHIPS: x]` parse could slip through).
- **Same defensive wrapping applied to `/discovery/{id}/init`** (the greeting endpoint) — rollback on save failure, wrapped chip generation, wrapped final yield.

### Changed
- `CLAUDE.md` → 2.2.1 (PATCH bump — internal robustness, no documented-feature behavior change)

---

## [2026-05-23] — Realtime Inbox

### Added
- **Realtime inbox stream** at `GET /api/v1/inbox/stream` — Server-Sent Events, Redis pub/sub backed. Pushes `hello` (initial count) on connect, then `update` events on every mutation (added / promoted / deleted). Replaces the previous 60s polling.
- **`app/services/inbox_pubsub.py`** — module-level helpers (`publish_event`, `subscribe`, `is_available`) using `redis.asyncio` pub/sub on channel `inbox:user:{user_id}`. Lazy-initialized client. Graceful no-op when `REDIS_URL` is empty.
- **`REDIS_URL`** env var added to `config.py` (optional in dev — empty disables realtime and the stream endpoint returns 503)
- **Instrumented mutation paths** to publish events: `POST /inbox`, `POST /inbox/{id}/promote`, `DELETE /inbox/{id}`, `POST /webhooks/inbound-email`
- **Frontend stream client** in `inboxStore.ts` — `connectStream()` opens an authenticated fetch+reader to the SSE endpoint, parses SSE event blocks, updates count via `refresh()` (idempotent — sidesteps race with same-tab `adjust()` calls). Auto-reconnect with exponential backoff (1s → 30s cap). Server-said-no (503) latches `_giveUp` so the client doesn't hammer.

### Changed
- **Sidebar.tsx**: removed the 60s `setInterval` polling loop. `useEffect` now calls `connectStream()` on mount and `disconnectStream()` on unmount. Mount-time `refresh()` retained for an instant count before the stream's hello arrives.
- **`webhooks.py`**: inbound-email handler now refreshes the persisted item and publishes the event AFTER the DB commit (best-effort — doesn't extend the transaction window).
- **`pyproject.toml`**: added `redis>=5.0,<6.0` dependency.
- `CLAUDE.md` → 2.2.0: feature 19 (Idea Inbox) expanded with realtime architecture, env var docs, and the new `/inbox/stream` endpoint

### Deployment note
- **Railway**: add a Redis service to the project and set `REDIS_URL` on the backend service. The backend will start fine without it (stream returns 503, badge updates on page navigation only).

---

## [2026-05-23] — Roadmap Refresh

### Changed
- `ROADMAP.md` → 2.0.0: full restructure with frontmatter, "Recently Shipped" section listing today's commits, trimmed Short-Term Polish (toast + fetchPathway wraps moved to shipped), added "Up Next" queue (realtime inbox → Notion integration), refreshed Open Product Questions, added admin-metrics dashboard to Medium-Term

### Added
- Admin-system reference in Medium-Term Features (Billing & admin section) and Tech Debt (orphan user row cleanup)
- Stop-hook-shaped "Up Next" queue so the next session can pick up without re-derivation

---

## [2026-05-23] — Doc-Versioning Enforcement

### Added
- **CLAUDE.md "Documentation Discipline" section** with end-of-session checklist (6 steps), list of versioned docs + frontmatter format, bump rules, enforcement layers
- **Critical Rule #9** in CLAUDE.md binding every code-touching task to the discipline checklist
- **DOC_VERSIONING.md and CHANGELOG.md** added to Session Recovery's read-on-start list
- **Stop hook** at `.claude/hooks/check-doc-versioning.sh` that fires when a Claude Code session ends. Inspects the latest commit — if it touched `frontend/src/` or `backend/app/` files without touching CHANGELOG.md, prints a non-blocking reminder.
- **`.claude/settings.json`** registers the Stop hook under `hooks.Stop` (project-level config, committed to git)
- **`.claude/projects/.../memory/doc-versioning.md`** — project memory entry so the convention persists across all Claude conversations

### Changed
- `CLAUDE.md` → 2.1.0 (was 2.0.0): added Documentation Discipline section, Critical Rule #9, updated Session Recovery list
- `DOC_VERSIONING.md` → 1.1.0 (was 1.0.0): added Enforcement section describing the three layers (CLAUDE.md prominence, project memory, Stop hook)

---

## [2026-05-23] — Admin System, Error UX, Doc Versioning

### Added
- **Admin dashboard** at hidden `/admin` route (commit `3747eac`)
  - Backend: `/api/v1/admin/*` router with `require_admin` dep
  - Endpoints: list/detail users (paginated, searchable), change plan, set entitlement overrides, grant admin, audit log
  - Frontend: lazy-loaded Admin page with Users + Audit Log tabs, drawer with plan toggle / override editor / admin grant
  - `users.is_admin` (bool) and `users.entitlement_overrides` (JSONB) columns
  - `admin_audit_log` table (append-only record of every admin action)
  - `adminStore` (Zustand) for user list, detail, audit list with optimistic mutations
  - Sidebar shows "Admin" link conditional on `user.is_admin`
- **DB migrations 027 + 028**
- **Doc versioning system**: `DOC_VERSIONING.md` convention + this `CHANGELOG.md`
- **Frontmatter** (Version + Last updated + CHANGELOG link) on all versioned docs

### Changed
- `entitlement_service.get_limits()` now merges `users.entitlement_overrides` over plan defaults — any key present in overrides wins; `null` means unlimited
- `UserProfile` schema exposes `is_admin` field for frontend gating
- `AuthUser` interface in `authStore` includes `is_admin: boolean`

### Security
- **Railway env vars activated**: `CORS_ORIGINS`, `CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTIES` — production JWT hardening now enforces tokens originate from this Clerk instance and authorized origins
- Self-revoke of admin status blocked at the API layer (prevents lockout)

### Fixed
- **~40 silent failure sites converted to user-visible toasts** across 18 components (commit `28ead2d`)
  - Discovery, Blocks, Library, Pipeline, Exports, PromptKit, MarketAnalysis, SprintPlanner, PitchMode, ShareDialog, TranscriptExportMenu, TemplateGrid, ModuleSession, PathwayExecute
  - Removed inline error banners in Profile, CommentSection, StarRating, billing/UpgradeModal in favor of toasts
- Wrap unhandled `fetchPathway()` rejections in `ModuleSession.tsx:73` and `PathwayExecute.tsx:43` (404s stay silent; other failures toast)
- Added `toast.success()` on milestones: import, snapshot save/restore, share link create/revoke, comment post

---

## [2026-05-22] — Mobile Viewport + Audit Cleanup

### Added
- `.h-dvh` and `.pb-mobile-nav` Tailwind utilities for iOS-safe viewport sizing (commit `fb1f1b8`)
- Save Place button in Discovery TopBar (commit `9c5ef1c`)
- VoiceMicButton wired into Discovery input row (commit `5db42eb`)
- Drag-and-drop Blocks board via `@dnd-kit/core` (commit `5db42eb`)
- AI partner picker per inbox item (commit `253b30a`)
- PitchMode React Flow user-flow diagram from MVP blocks (commit `253b30a`)
- `inboxStore` (Zustand) for sidebar unread badge with 60s polling
- `react-hot-toast` globally wired in `App.tsx`

### Changed
- SSE event order in Discovery: `sheet_update` now fires BEFORE `done` (so clients that close on done sentinel still receive sheet updates)
- `auth.py` race handling consolidated with `INSERT ... ON CONFLICT (clerk_user_id) DO NOTHING`
- `ui/UpgradeModal.tsx` renamed to `ui/EntitlementLimitModal.tsx` to disambiguate from the plan picker

### Fixed
- Transcript copy now includes AI messages (Axios `responseType: 'text'` for markdown response)
- PathwayReview Proceed-button errors now surface via toast + inline banner instead of infinite spinner
- Mobile viewport conformance across 19 pages — `h-screen` (100vh) replaced with `.h-dvh`, `pb-14` replaced with `.pb-mobile-nav`
- iPhone home indicator no longer overlaps bottom nav (safe-area-inset applied)
- 8 audit findings closed with 2-agent verification per fix (commit `253b30a`)

---

## [2026-05-21] — Post-Update Audit

### Added
- Backend test infrastructure (37 tests passing)
- Centralized entitlement guards on all creation paths (free=3 projects / basic=25 / pro=unlimited)
- Private share viewer JWT tokens (6-hour, HS256)
- Svix webhook verification + Resend inbound email idempotency (migration 025)

### Changed
- Discovery autosave rewritten with ref-based pattern (no message-array overwrite)
- Library resume routing now gates on Discovery stage before routing past Discovery
- Pathway completion sync after module complete/skip

### Fixed
- Empty-session recovery now prefers non-empty session via `jsonb_array_length`
- Frontend lint cleanup — zero errors

---

## [2026-05-22] _(earlier)_ — Auth Race + Discovery Polish

### Fixed
- Duplicate user crash (auth.py race handling + migration 026 dedup)
- Quick chips always appear (event_stream try/except wrapping)
- Design sheet update fix (`extract_sheet_fields` JSON parsing robustness)
- AI partner anti-repetition (CONVERSATION RULES block with message_count)

---

## Format note

Doc-only changes (e.g. bumping CLAUDE.md version after a content tweak) belong in the same entry as the code change they describe. Standalone doc-only bumps (typo fixes, version-table refreshes) are batched into a small "Doc cleanup" entry at the next release date.
