# Discovery Resume And Autosave Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-entering discovery for a project resumes the latest active session with saved messages, stage, partner style, and sheet state instead of starting a fresh conversation.

**Architecture:** Make `/discovery/start` idempotent by default. The backend should return an existing active session when one exists, and only create a new session when explicitly requested. The frontend should treat the returned session as canonical and load the current design sheet on entry.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL JSONB, React, TypeScript, Axios, existing `useSSE` hook.

---

## File Structure

- Modify: `backend/app/schemas/session.py`
  - Add `force_new: bool = False` to `SessionCreate`.
- Modify: `backend/app/services/discovery_service.py`
  - Add a latest-session fetch helper.
  - Add a create-or-resume helper.
- Modify: `backend/app/routers/discovery.py`
  - Use the create-or-resume helper in `start_session`.
  - Ensure project partner style is inherited only for newly created sessions or empty legacy sessions.
- Modify: `frontend/src/pages/Discovery.tsx`
  - Load returned session messages/stage.
  - Fetch current design sheet after session start/resume.
  - Save progress on page hide/unmount.
- Add or update backend tests:
  - `backend/tests/test_discovery_resume.py`
- Add or update frontend tests only if the project already has a frontend test harness. It currently does not.

## Expected Behavior

Fresh project:

1. `POST /discovery/start` creates a session.
2. Frontend sees no messages and calls `/discovery/{session_id}/init`.
3. Assistant greeting streams and is saved.

Existing active project:

1. `POST /discovery/start` returns latest active session.
2. Frontend sets `sessionId`, `messages`, `stage`, and `partnerStyle`.
3. Frontend fetches `/discovery/{session_id}/sheet`.
4. Frontend does not call `/init` if messages already exist.

Explicit new session:

1. Caller sends `{ "project_id": "...", "force_new": true }`.
2. Backend creates a new session.

## Task 1: Extend SessionCreate

**Files:**
- Modify: `backend/app/schemas/session.py`

- [ ] **Step 1: Add the field**

Change `SessionCreate` to:

```python
class SessionCreate(BaseModel):
    """Schema for starting or resuming a discovery session."""
    project_id: uuid.UUID
    force_new: bool = False
```

- [ ] **Step 2: Confirm Pydantic accepts old callers**

Existing frontend payloads send only `project_id`. Pydantic will default `force_new` to `False`, so this is backward compatible.

## Task 2: Add Backend Resume Helpers

**Files:**
- Modify: `backend/app/services/discovery_service.py`

- [ ] **Step 1: Add latest active session helper**

Add this below `create_session` or near fetchers:

```python
async def get_latest_active_session_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> DiscoverySession | None:
    """Return the latest active discovery session for a project, if any."""
    result = await db.execute(
        select(DiscoverySession)
        .where(
            DiscoverySession.project_id == project_id,
            DiscoverySession.status == "active",
        )
        .order_by(DiscoverySession.updated_at.desc(), DiscoverySession.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

- [ ] **Step 2: Add create-or-resume helper**

```python
async def create_or_resume_session(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    force_new: bool = False,
) -> tuple[DiscoverySession, bool]:
    """Return an active session for the project.

    Returns:
        (session, created)
    """
    if not force_new:
        existing = await get_latest_active_session_for_project(db, project_id)
        if existing:
            return existing, False

    session = await create_session(db, project_id)
    return session, True
```

- [ ] **Step 3: Keep old `create_session` behavior for explicit new sessions**

Do not remove `create_session`. Other code and tests may still call it when a brand-new row is required.

## Task 3: Make `/discovery/start` Idempotent

**Files:**
- Modify: `backend/app/routers/discovery.py`

- [ ] **Step 1: Replace direct create call**

Current code:

```python
session = await discovery_service.create_session(db, payload.project_id)
# Inherit AI partner style from project
session.ai_partner_style = getattr(project, "ai_partner_style", "strategist")
await db.commit()
```

Replace with:

```python
session, created = await discovery_service.create_or_resume_session(
    db,
    payload.project_id,
    force_new=payload.force_new,
)

if created or not getattr(session, "ai_partner_style", None):
    session.ai_partner_style = getattr(project, "ai_partner_style", "strategist")

await db.commit()
await db.refresh(session)
```

- [ ] **Step 2: Keep ownership check before resume**

Do not move the existing project ownership query below the resume call. A user must not be able to discover whether another user's project has an active session.

- [ ] **Step 3: Do not call `/init` from backend**

Keep the greeting stream separate. The frontend already skips `/init` when messages exist.

## Task 4: Load Sheet State On Discovery Entry

**Files:**
- Modify: `frontend/src/pages/Discovery.tsx`

- [ ] **Step 1: Add a helper inside the component**

Add after the pathway-loading effect or before the init effect:

```tsx
const loadSheet = useCallback(async (id: string) => {
  try {
    const { data } = await apiClient.get(`/discovery/${id}/sheet`)
    setSheet({
      problem: data.problem ?? undefined,
      audience: data.audience ?? undefined,
      mvp: data.mvp ?? undefined,
      features: data.features ?? undefined,
      tone: data.tone ?? undefined,
      platform: data.platform ?? undefined,
      tech_constraints: data.tech_constraints ?? undefined,
      success_metric: data.success_metric ?? undefined,
      confidence_score: data.confidence_score ?? 0,
      fields_data: data.fields_data ?? undefined,
    } as SheetData)
  } catch {
    setSheet({ confidence_score: 0 })
  }
}, [])
```

Update the local `SheetData` interface to include:

```tsx
fields_data?: Record<string, unknown>
```

- [ ] **Step 2: Call it after session start/resume**

In the init effect, after `setSessionId(data.id)`, add:

```tsx
await loadSheet(data.id)
```

The relevant block should become:

```tsx
const { data } = await apiClient.post('/discovery/start', { project_id: projectId })
if (cancelled) return

setSessionId(data.id)
await loadSheet(data.id)

if (data.ai_partner_style) setPartnerStyle(data.ai_partner_style)
```

- [ ] **Step 3: Add `loadSheet` to the init effect dependencies**

The init effect dependency list should include `projectId`, `send`, and `loadSheet`. If adding `send` changes behavior due callback identity, keep the existing eslint suppression but include `loadSheet`.

## Task 5: Save On Page Hide And Unmount

**Files:**
- Modify: `frontend/src/pages/Discovery.tsx`

- [ ] **Step 1: Add a stable save helper**

```tsx
const saveProgress = useCallback(async () => {
  if (!sessionId || messages.length === 0) return
  await apiClient.patch(`/discovery/${sessionId}/progress`, {
    messages,
    stage,
  })
}, [sessionId, messages, stage])
```

- [ ] **Step 2: Reuse it in the interval effect**

Replace the nested `saveProgress` function in the 30-second autosave effect with the helper:

```tsx
useEffect(() => {
  if (!sessionId || messages.length === 0) return

  autoSaveTimerRef.current = setInterval(() => {
    saveProgress().catch((err) => console.error('Auto-save failed:', err))
  }, AUTO_SAVE_INTERVAL_MS)

  return () => {
    if (autoSaveTimerRef.current) {
      clearInterval(autoSaveTimerRef.current)
      autoSaveTimerRef.current = null
    }
  }
}, [sessionId, messages.length, saveProgress])
```

- [ ] **Step 3: Add page visibility save**

```tsx
useEffect(() => {
  const handleVisibilityChange = () => {
    if (document.visibilityState === 'hidden') {
      saveProgress().catch((err) => console.error('Visibility save failed:', err))
    }
  }

  document.addEventListener('visibilitychange', handleVisibilityChange)
  return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
}, [saveProgress])
```

- [ ] **Step 4: Add unmount save**

```tsx
useEffect(() => {
  return () => {
    saveProgress().catch((err) => console.error('Unmount save failed:', err))
  }
}, [saveProgress])
```

Note: Backend message endpoints already persist canonical messages. This save is mainly for stage/local state consistency and for any UI-added assistant/system messages such as partner switch notices.

## Task 6: Add Backend Tests

**Files:**
- Add: `backend/tests/test_discovery_resume.py`
- Potentially add test dependencies if the backend test environment is formalized later.

- [ ] **Step 1: Add a service-level test using mocked session methods**

If no database test fixture exists, add a focused unit test around helper behavior with a fake object is not enough because SQLAlchemy query behavior matters. Prefer adding a real async database fixture in a follow-up. For now, add a regression test file that documents desired API behavior and can be wired to the project's test database.

Create:

```python
import uuid

import pytest
from sqlalchemy import select

from app.models.project import Project
from app.models.session import DiscoverySession
from app.services.discovery_service import create_or_resume_session


@pytest.mark.asyncio
async def test_create_or_resume_returns_existing_active_session(db_session, test_user):
    project = Project(
        user_id=test_user.id,
        name="Resume Test",
        description="Test project",
    )
    db_session.add(project)
    await db_session.flush()

    first, created_first = await create_or_resume_session(db_session, project.id)
    await db_session.commit()

    second, created_second = await create_or_resume_session(db_session, project.id)

    assert created_first is True
    assert created_second is False
    assert second.id == first.id

    rows = await db_session.execute(
        select(DiscoverySession).where(DiscoverySession.project_id == project.id)
    )
    assert len(rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_create_or_resume_force_new_creates_second_session(db_session, test_user):
    project = Project(
        user_id=test_user.id,
        name="Force New Test",
        description="Test project",
    )
    db_session.add(project)
    await db_session.flush()

    first, _ = await create_or_resume_session(db_session, project.id)
    await db_session.commit()

    second, created_second = await create_or_resume_session(
        db_session,
        project.id,
        force_new=True,
    )

    assert created_second is True
    assert second.id != first.id
```

- [ ] **Step 2: If `db_session` and `test_user` fixtures do not exist, create them**

Add a separate test infrastructure task before enabling this test. Do not fake this test as passing without real fixtures.

## Task 7: Manual Acceptance Checklist

- [ ] Create a new project.
- [ ] Enter discovery and wait for greeting.
- [ ] Send two messages.
- [ ] Navigate to Library.
- [ ] Open the same project.
- [ ] Confirm the previous greeting and two messages are visible.
- [ ] Confirm stage is not reset to `greeting` if it had advanced.
- [ ] Confirm design sheet confidence and fields display immediately.
- [ ] Refresh the browser on the discovery page.
- [ ] Confirm the same session resumes.
- [ ] Start a new session only with `force_new: true` from an explicit UI action, if such UI is later added.

