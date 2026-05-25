# Frontend Quality, Tests, Branching, And Docs Implementation Plan

> For Claude Code: execute this plan after the P0 persistence and security fixes. Do not start a dev server or take screenshots unless the project instructions change.

## Goal

Bring the codebase to a maintainable state after the update by making lint pass, making tests runnable, completing branch/snapshot semantics, and aligning docs with code.

## Task 1: Make Frontend Lint Pass

### Files

Start with:

- `frontend/src/components/tutorial/StageInterlude.tsx`
- `frontend/src/components/home/TemplateGrid.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/partner/PartnerSelector.tsx`
- `frontend/src/components/sharing/FeedbackPanel.tsx`
- `frontend/src/pages/CategorySelect.tsx`
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/MarketAnalysis.tsx`
- `frontend/src/pages/ModuleSession.tsx`
- `frontend/src/pages/PathwayExecute.tsx`
- `frontend/src/pages/PathwayReview.tsx`

### Step 1: Fix `StageInterlude` hook ordering

Current issue:

```tsx
useEffect(() => {
  if (!visible) return
  const timer = setTimeout(() => dismiss(), 4000)
  return () => clearTimeout(timer)
}, [visible])

const dismiss = () => {
  setVisible(false)
  markInterludeSeen(phase)
}
```

Fix:

```tsx
const dismiss = useCallback(() => {
  setVisible(false)
  markInterludeSeen(phase)
}, [markInterludeSeen, phase])

useEffect(() => {
  if (!visible) return
  const timer = setTimeout(dismiss, 4000)
  return () => clearTimeout(timer)
}, [visible, dismiss])
```

### Step 2: Fix cache hydration effects without synchronous setState-in-effect

For `TemplateGrid`, prefer lazy initializers and derived state:

```tsx
const [templates, setTemplates] = useState<Template[]>(() => _templateCache ?? [])
const [loading, setLoading] = useState(() => !_templateCache)
const activeCategory = category || internalCategory
```

If a prop controls category, avoid mirroring it into state unless local edits are needed.

For cached partner styles in `Home`, use the same pattern.

### Step 3: Fix `MarketAnalysis` render mutation

Current issue:

```tsx
let cumulative = 0
const gradientStops = segments.map(seg => {
  const start = cumulative
  cumulative += seg.pct
  return `${seg.color} ${start}% ${cumulative}%`
})
```

Replace with a reducer or precomputed loop outside JSX-sensitive render mutation:

```tsx
const gradientStops = useMemo(() => {
  let total = 0
  return segments.map((seg) => {
    const start = total
    total += seg.pct
    return `${seg.color} ${start}% ${total}%`
  })
}, [segments])
```

If `segments` is built inline, memoize it too or compute all values in one `useMemo`.

### Step 4: Fix missing hook dependencies

Do not silence lint unless there is a written reason. Prefer:

- Move logic into the effect.
- Use `useCallback` for functions passed into effects.
- Use refs only for event handlers that must be stable.

Known locations:

- `Sidebar.tsx`
- `ShareDialog.tsx`
- `ModuleSession.tsx`
- `PathwayExecute.tsx`
- `PathwayReview.tsx`

### Step 5: Fix Fast Refresh export rule

`CategorySelect.tsx` exports constants/functions alongside a component. Move shared constants to:

```text
frontend/src/lib/categories.ts
```

or:

```text
frontend/src/types/categories.ts
```

Then leave `CategorySelect.tsx` exporting only React components.

### Step 6: Verify

Run:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

Do not stop at build passing. Lint must pass.

## Task 2: Make Backend Tests Runnable

### Files

- Add `backend/tests/conftest.py`
- Modify `backend/tests/test_discovery_resume.py`
- Add new tests for library/pathway/security behavior

### Step 1: Decide test database approach

Use one of these:

Option A: PostgreSQL test database.

- Best fidelity because app uses JSONB and PostgreSQL-specific `DISTINCT ON`.
- Requires `TEST_DATABASE_URL`.

Option B: SQLite async for service-level tests.

- Faster, but JSONB/Postgres-specific queries will not be covered.
- Not recommended for library query tests.

Prefer Option A for this app.

### Step 2: Add fixtures

Example:

```python
import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.database import Base
from app.models.user import User

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for async database tests",
)

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
      await conn.run_sync(Base.metadata.drop_all)
      await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
      yield session

    await engine.dispose()

@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(email="test@example.com", clerk_user_id="user_test", email_verified=True)
    db_session.add(user)
    await db_session.flush()
    return user
```

Adjust indentation and imports to project style.

### Step 3: Add regression tests

Add tests for:

- Non-empty session is preferred over newer empty session.
- Progress save with stale `client_message_count` does not overwrite messages.
- Library resume path sends `confirm` stage to pathway review.
- Completing all modules marks pathway complete.
- Private share comments require viewer access token.
- Template use checks project limit.
- Inbox promote checks project limit.
- Branch creation checks project limit.
- `.ideai` import checks project limit.

## Task 3: Complete Branching And Snapshot Semantics

### Files

- Modify `backend/app/routers/branching.py`
- Modify `backend/app/services/library_service.py`
- Add tests
- Add frontend compare/merge UI only if the feature remains user-facing

### Step 1: Copy every gathered field

`_gather_project_state` includes:

- project metadata
- design sheet
- discovery sessions
- blocks
- pipeline
- market analysis
- prompt kits
- sprint plan
- module pathway
- module responses

Make `_copy_child_records` support the same fields.

Specific missing fields:

- `DesignSheet.fields_data`
- `DiscoverySession.ai_partner_style`
- `ModuleResponse.completed_at`
- `MarketAnalysis`

### Step 2: Avoid merge data loss

Current `merge_branch` deletes parent `MarketAnalysis`, but `_copy_child_records` does not restore branch market analysis. Fix that before merge is exposed.

### Step 3: Preserve completed timestamps

When restoring module responses:

```python
completed_at=parse_iso_datetime(mr.get("completed_at"))
```

Add a small parser helper that handles null safely.

### Step 4: Decide frontend scope

If compare/merge should be user-facing, add a Library branch section:

- list branches
- compare selected branch
- merge branch with explicit confirmation modal

If not in scope, update docs to say backend endpoints exist but frontend branch management is pending.

## Task 4: Align Docs And Environment Files

### Files

- `AGENTS.md`
- `CLAUDE.md`
- `CONTEXT_HANDOFF.md`
- `README.md`
- `frontend/README.md`
- `env.example`
- `ARCHITECTURE.md`
- `DEPLOYMENT_RAILWAY.md`

### Step 1: Fix env names

Code uses:

```text
ANTHROPIC_KEY
```

Docs currently also mention:

```text
ANTHROPIC_API_KEY
```

Choose one. The least risky change is to update docs to `ANTHROPIC_KEY`.

Optionally support both in code:

```python
ANTHROPIC_KEY: str = ""
ANTHROPIC_API_KEY: str = ""

@property
def anthropic_api_key(self) -> str:
    return self.ANTHROPIC_KEY or self.ANTHROPIC_API_KEY
```

Then update all services to use `settings.anthropic_api_key`.

### Step 2: Fix email domains

Update `env.example`:

```env
FROM_EMAIL=noreply@send.myide.ai
INBOX_DOMAIN=inbox.myide.ai
```

### Step 3: Add missing security env vars

Add:

```env
RESEND_WEBHOOK_SECRET=
INTEGRATION_TOKEN_KEY=
CLERK_ISSUER=
CLERK_AUDIENCE=
CLERK_AUTHORIZED_PARTIES=[]
SHARE_ACCESS_SECRET=
```

For `CLERK_AUTHORIZED_PARTIES`, be explicit that Pydantic expects JSON unless a custom parser is implemented.

### Step 4: Update migration chain

Docs must mention migration 024:

```text
024 - Replace system templates with 160 templates across 16 concept categories.
```

### Step 5: Update stale frontend docs

Replace `frontend/README.md` with a short Ide/AI frontend guide:

- scripts
- env vars
- Tailwind v4 note
- no local preview requirement for Codex
- build/lint commands

### Step 6: Resolve AGENTS versus CLAUDE source of truth

The user supplied AGENTS.md as the session source of truth, but the repo also has CLAUDE.md. They must not conflict.

Update AGENTS.md to match current code:

- React 19.2
- Claude model naming
- migration 024
- actual Zustand stores
- current integrations scope
- current docs status

## Task 5: Product UX Completion

### Files

- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/PromptKit.tsx`
- `frontend/src/pages/MarketAnalysis.tsx`
- `frontend/src/pages/SprintPlanner.tsx`
- `frontend/src/pages/Library.tsx`
- `frontend/src/components/billing/UpgradeModal.tsx`

### Step 1: Show entitlement errors

Create a helper:

```tsx
export function getApiErrorMessage(err: unknown): string
export function isEntitlementError(err: unknown): boolean
```

Use it to show:

- inline error text
- upgrade modal
- toast if toast system exists

### Step 2: Improve empty states

PromptKit:

- If design sheet missing, show "Complete Discovery first" and link to Library recommended path.
- If 403, show upgrade modal.

Market:

- If 403, show upgrade modal.
- If generation fails mid-stream, preserve any completed sections.

Sprint:

- If no blocks, link to Blocks.
- If 403 after entitlement enforcement, show upgrade modal.

Library:

- If resume path and progress label disagree, backend should be fixed first, but frontend can display the exact resume destination as a small debug-free label like "Next: Pathway Review".

## Task 6: Verification

Run:

```powershell
git status --short
cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd audit --json
```

Backend:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q
```

With test dependencies and database:

```powershell
cd backend
$env:TEST_DATABASE_URL='postgresql+asyncpg://...'
python -m pytest tests -q
```

