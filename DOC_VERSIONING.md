# Doc Versioning Convention

> **Version:** 1.0.0 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)

Single source of truth for how Ide/AI documentation is versioned and kept consistent with the codebase. Read this once; refer back when you commit anything that touches a versioned doc.

---

## Which docs are versioned

These follow this convention:

| Doc | Purpose |
|-----|---------|
| `CLAUDE.md` | Project identity, features, critical rules — read first on every session |
| `CONTEXT_HANDOFF.md` | Latest session state — what just shipped, what's open |
| `TODO.md` | Prioritized concrete next steps |
| `MEMORY.md` | Conventions, pitfalls, architecture mental model |
| `ROADMAP.md` | Forward direction |
| `ARCHITECTURE.md` | Architecture diagrams + system design |
| `PRD.md` / `FEATURE_SPEC.md` | Product requirements + feature specs |
| `PRODUCT_DESCRIPTION.md` / `SYSTEM_PROMPT.md` | Marketing + AI configuration |
| `AI_PARTNER_SELECTOR_SPEC.md` | AI partner system spec |
| `DEPLOYMENT_RAILWAY.md` | Deployment runbook |
| `PROMPT_SEQUENCE.md` | Prompt flow documentation |
| `DOC_VERSIONING.md` (this file) | The convention itself |
| `CHANGELOG.md` | Project + doc changelog |

**Not versioned:** READMEs, ad-hoc audit packages under `docs/`, code comments, frontend/backend READMEs.

---

## Frontmatter format

Each versioned doc carries one header line immediately after its H1 title:

```markdown
# CLAUDE.md — Ide/AI

> **Version:** 3.0.0 · **Last updated:** 2026-05-23 · See [CHANGELOG.md](CHANGELOG.md)

(rest of doc...)
```

Three fields, separated by `·` (middle dot). Keep it on a single line — terse is the point.

---

## When to bump

Follows [SemVer](https://semver.org/), applied per-doc.

### MAJOR (X.0.0)

Bump when:
- The doc is restructured (sections reordered, headings renamed)
- An entire new section is added that changes how the doc is read
- Content contradicts the previous version (an old fact is now wrong)

Examples:
- Adding a new top-level feature section ("Admin Dashboard") to CLAUDE.md → MAJOR
- Renaming "Modular Pathway" to "Concept Pathway" everywhere → MAJOR
- Splitting CONTEXT_HANDOFF.md into per-session files → MAJOR

### MINOR (X.Y.0)

Bump when:
- New content added within an existing section
- A new row in a table (e.g. new migration, new env var, new endpoint)
- A new feature listed without restructure

Examples:
- Adding migration 027 to the migrations table → MINOR
- Adding `CLERK_ISSUER` to env var list → MINOR
- Marking a TODO item complete and moving it to Recently Done → MINOR

### PATCH (X.Y.Z)

Bump when:
- Typo, broken link, formatting cleanup
- Clarifying a sentence without changing meaning
- Updating a version number table without semantic change

Group multiple typo fixes into one bump if they're in the same commit.

---

## When to add a CHANGELOG entry

| Change type | Add CHANGELOG entry? |
|-------------|--------------------|
| Doc MAJOR bump | **Yes** |
| Doc MINOR bump | **Yes** |
| Doc PATCH bump | Optional — group with other small fixes |
| Code change with no doc impact | No (covered by git log) |
| Code change that should update a doc | **Yes** — update the doc AND log the change |

Format follows [Keep a Changelog 1.1](https://keepachangelog.com/en/1.1.0/):

```markdown
## [YYYY-MM-DD] — Short release name

### Added
- New things shipped

### Changed
- Modified behavior

### Fixed
- Bug fixes

### Security
- Auth / hardening / secrets-related changes
```

Newest entries at the top. An `[Unreleased]` section at the very top collects in-progress work between releases.

---

## The checklist

When you finish work that touches code AND a versioned doc, run through this:

- [ ] Updated the affected sections of CLAUDE.md / CONTEXT_HANDOFF.md / TODO.md as needed
- [ ] Bumped the `Version` field on each doc you touched
- [ ] Updated the `Last updated` date on each doc you touched
- [ ] Added a CHANGELOG.md entry (Added / Changed / Fixed / Security)
- [ ] Commit message follows conventional-commits format

When you finish work that touches **only** code (and the docs are still accurate), no doc bump is needed. Trust the discipline: if you're unsure whether a change is doc-worthy, err on the side of writing it down. Docs drift faster than you'd expect.

---

## Why this convention

We chose SemVer-per-doc + a root CHANGELOG + manual discipline (no CI enforcement) because:

1. **Per-doc versions** let readers see at a glance which docs are stale (mismatched dates vs. recent commits).
2. **Root CHANGELOG** gives a single skimmable "what happened this month" view that survives even if individual docs are restructured.
3. **Manual discipline** is the right starting point — automation can come later if drift becomes a problem. Pre-commit hooks or PR-checks would add friction for a one-developer codebase.

If at any point doc drift becomes routine, revisit and add a lightweight pre-commit hook that checks for CHANGELOG updates on `.md` file changes.
