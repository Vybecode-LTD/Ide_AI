# Changelog

All notable changes to Ide/AI and its documentation. Format based on [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/). Doc versioning follows [DOC_VERSIONING.md](DOC_VERSIONING.md).

## [Unreleased]

_Nothing yet._

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
