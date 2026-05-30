# SOFTWARE RELEASE — Not Applicable to Ide/AI

> **Status:** N/A for this project — kept as a stub so the conditional `@SOFTWARE_RELEASE.md`
> references in the other directives still resolve, and so the vendored kit's directive set stays
> complete. The full desktop-release directive was intentionally removed.

This directive governs **desktop applications distributed as a downloadable installer / binary**
(`ONLY_IF_DESKTOP_DOWNLOAD_APP`). **Ide/AI is a web app, not a desktop download — so it does not
apply.**

## How Ide/AI actually ships

- **Push to `main` → Railway auto-deploys** both public services (backend + frontend). No installer,
  no malware-scan step, no GitHub Release, no `"release it"` pipeline.
- **Database migrations** run automatically via the `alembic upgrade head` pre-deploy hook; a failed
  migration rolls the deploy back.
- **Versioning of note** lives in [DOC_VERSIONING.md](DOC_VERSIONING.md) (per-doc SemVer) and
  [CHANGELOG.md](CHANGELOG.md) — not a desktop release flow.

## If this ever becomes a desktop app

Restore the full directive from the Claude-Kit master copy (`Development/SOFTWARE_RELEASE.md`),
remove this stub, and wire it into [CLAUDE.md](CLAUDE.md)'s Binding Directives section.
