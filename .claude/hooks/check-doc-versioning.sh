#!/bin/bash
# check-doc-versioning.sh — Stop hook for Ide/AI
#
# Fires when a Claude Code session ends. Inspects the latest commit on the
# current branch and warns (non-blocking) if it touched code under
# frontend/src/ or backend/app/ without also touching CHANGELOG.md.
#
# Per DOC_VERSIONING.md, code changes that affect documented features should
# be accompanied by a CHANGELOG entry. This hook is a gentle reminder — it
# always exits 0 so it never blocks anything.

set -u
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR" 2>/dev/null || exit 0

# Skip silently if not in a git repo
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

# Files changed in the latest commit
LAST_COMMIT_FILES=$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null)

# Nothing to inspect (root commit or detached HEAD)
[ -z "$LAST_COMMIT_FILES" ] && exit 0

# Was any code touched? (frontend/src or backend/app)
HAS_CODE=$(printf '%s\n' "$LAST_COMMIT_FILES" | grep -E '^(frontend/src|backend/app)/' | head -1)

# Pure doc / config commit — no nag
[ -z "$HAS_CODE" ] && exit 0

# Was CHANGELOG.md included?
HAS_CHANGELOG=$(printf '%s\n' "$LAST_COMMIT_FILES" | grep -E '^CHANGELOG\.md$' | head -1)

# Code touched + CHANGELOG touched → fine
[ -n "$HAS_CHANGELOG" ] && exit 0

# Nag — code without CHANGELOG
COMMIT_SHA=$(git log -1 --format='%h' 2>/dev/null)
COMMIT_SUBJECT=$(git log -1 --format='%s' 2>/dev/null)
FILE_COUNT=$(printf '%s\n' "$LAST_COMMIT_FILES" | wc -l | tr -d ' ')

cat >&2 <<EOF

⚠️  Doc-versioning reminder
    Latest commit ${COMMIT_SHA} ("${COMMIT_SUBJECT}") touched ${FILE_COUNT} file(s)
    under code paths but did NOT update CHANGELOG.md.

    If this commit changed a documented feature, please:
      1. Add a CHANGELOG.md entry under [Unreleased] or a new dated section
      2. Bump version + Last updated on any affected versioned doc
      3. See DOC_VERSIONING.md for the full convention

    To suppress this warning for a legitimate refactor (no doc impact),
    you can still amend the commit with a one-line CHANGELOG note under
    "### Changed — Internal" or commit a docs-only follow-up.

EOF

exit 0
