# Discovery, Library, And Pathway Resume Implementation Plan

> For Claude Code: implement this plan task by task. Use checkboxes for tracking. Do not start a dev server or browser preview. Run build/lint/backend syntax checks after changes.

## Goal

Make project progress durable and resumable across Discovery, Library, and modular pathway execution.

## Architecture

Use the backend as the canonical source of truth for persisted messages and pathway state. The frontend may optimistically display messages, but it must not overwrite the backend with stale arrays.

## Task 1: Replace Destructive Discovery Progress Saves

### Files

- Modify `frontend/src/pages/Discovery.tsx`
- Modify `backend/app/routers/discovery.py`
- Modify `backend/app/schemas/session.py`
- Add tests under `backend/tests/`

### Current Problem

`Discovery.tsx` calls `saveProgress` from effect cleanup. Because `saveProgress` depends on `messages` and `stage`, the cleanup runs when those dependencies change. It can save older messages over newer backend state.

### Step 1: Remove message-array overwrite from normal autosave

Change the progress schema from:

```python
class ProgressPayload(BaseModel):
    messages: list = []
    stage: str
```

To a safer shape:

```python
class ProgressPayload(BaseModel):
    stage: str | None = None
    client_message_count: int | None = None
```

Do not accept arbitrary `messages` from the browser for normal autosave.

If preserving unsent draft text is desired, use:

```python
draft: str | None = None
```

and store it in a new nullable JSON field later. Do not overload `messages` for this.

### Step 2: Change progress endpoint behavior

In `backend/app/routers/discovery.py`, replace:

```python
session.messages = payload.messages
session.stage = payload.stage
```

With:

```python
if payload.stage:
    session.stage = payload.stage
```

If `client_message_count` is supplied, validate but do not mutate messages:

```python
server_count = len(session.messages or [])
if payload.client_message_count is not None and payload.client_message_count < server_count:
    # Client is stale. Keep server state.
    return {
        "status": "ignored_stale_client",
        "session_id": str(session_id),
        "server_message_count": server_count,
    }
```

### Step 3: Register true unmount/pagehide save using refs

In `frontend/src/pages/Discovery.tsx`, keep refs for latest values:

```tsx
const latestRef = useRef({
  sessionId: null as string | null,
  stage: 'greeting',
  messageCount: 0,
})

useEffect(() => {
  latestRef.current = {
    sessionId,
    stage,
    messageCount: messages.length,
  }
}, [sessionId, stage, messages.length])
```

Create a stable save function that reads refs:

```tsx
const saveProgressRef = useCallback(async () => {
  const latest = latestRef.current
  if (!latest.sessionId) return
  await apiClient.patch(`/discovery/${latest.sessionId}/progress`, {
    stage: latest.stage,
    client_message_count: latest.messageCount,
  })
}, [])
```

Register cleanup once:

```tsx
useEffect(() => {
  return () => {
    void saveProgressRef().catch((err) => console.error('Unmount save failed:', err))
  }
}, [saveProgressRef])
```

Register visibility save once:

```tsx
useEffect(() => {
  const handler = () => {
    if (document.visibilityState === 'hidden') {
      void saveProgressRef().catch((err) => console.error('Visibility save failed:', err))
    }
  }
  document.addEventListener('visibilitychange', handler)
  return () => document.removeEventListener('visibilitychange', handler)
}, [saveProgressRef])
```

### Step 4: Save only stage on interval and stage change

The interval should call the ref-based save. It should not depend on `messages` directly:

```tsx
useEffect(() => {
  if (!sessionId) return
  const timer = setInterval(() => {
    void saveProgressRef().catch((err) => console.error('Auto-save failed:', err))
  }, AUTO_SAVE_INTERVAL_MS)
  return () => clearInterval(timer)
}, [sessionId, saveProgressRef])
```

Stage-change save can use the same helper.

### Step 5: Abort in-flight SSE on unmount

`useSSE` returns `abort`. In `Discovery.tsx`, destructure it:

```tsx
const { send, abort, isStreaming } = useSSE(...)
```

Add:

```tsx
useEffect(() => {
  return () => abort()
}, [abort])
```

Then decide product behavior:

- If leaving during a stream should cancel the AI response, this is correct.
- If leaving during a stream should continue backend generation, use a server-side job model instead of an HTTP response stream.

For now, explicit abort is safer than letting state updates continue after unmount.

## Task 2: Recover Old Non-Empty Sessions

### Files

- Modify `backend/app/services/discovery_service.py`
- Add tests in `backend/tests/test_discovery_resume.py`

### Step 1: Add helper that prefers non-empty active sessions

PostgreSQL supports JSONB array length. Use SQLAlchemy functions carefully:

```python
from sqlalchemy import case, func

message_count = func.coalesce(func.jsonb_array_length(DiscoverySession.messages), 0)

result = await db.execute(
    select(DiscoverySession)
    .where(
        DiscoverySession.project_id == project_id,
        DiscoverySession.status == "active",
    )
    .order_by(
        case((message_count > 0, 0), else_=1),
        DiscoverySession.updated_at.desc(),
        DiscoverySession.created_at.desc(),
    )
    .limit(1)
)
```

If `messages` can be `null`, keep the `coalesce`.

### Step 2: Retire newer empty orphan sessions

After selecting a non-empty active session, optionally mark empty active siblings as abandoned:

```python
empty_sessions = await db.execute(
    select(DiscoverySession).where(
        DiscoverySession.project_id == project_id,
        DiscoverySession.status == "active",
        DiscoverySession.id != selected.id,
        func.coalesce(func.jsonb_array_length(DiscoverySession.messages), 0) == 0,
    )
)
for session in empty_sessions.scalars():
    session.status = "abandoned"
```

Do this only when a non-empty selected session exists.

### Step 3: Add regression tests

Add tests for:

- Latest empty active session plus older non-empty active session returns non-empty.
- Empty sibling sessions are marked abandoned when non-empty session is resumed.
- `force_new=True` still creates a fresh session.

## Task 3: Make Discovery Completion Explicit

### Files

- Modify `backend/app/services/discovery_service.py`
- Modify `backend/app/routers/discovery.py`
- Modify `backend/app/routers/library.py`
- Modify `frontend/src/pages/Library.tsx` only if labels need adjustment

### Step 1: Define completion

Use this rule:

- `stage == "confirm"` means discovery has enough structured data to proceed.
- `status == "completed"` means user explicitly completed/confirmed discovery.

If there is no explicit confirmation UI yet, Library should treat `stage == "confirm"` as eligible for pathway review even if `status == "active"`.

### Step 2: Fix `_compute_resume_path`

Change the beginning of `_compute_resume_path` from:

```python
if not session_status or session_status == "active":
    return f"/discovery/{pid}"
```

To:

```python
discovery_done = discovery_stage in {"confirm", "complete"} or session_status == "completed"
if not discovery_done:
    return f"/discovery/{pid}"
```

Then keep the pathway/block logic after that.

### Step 3: Optionally mark status complete

When `next_stage` moves to the last stage, consider:

```python
if new_stage in {"confirm", "complete"}:
    session.status = "completed"
```

Only do this if the product wants automatic completion. If users should review and explicitly confirm, add a route instead:

```python
@router.post("/{session_id}/complete")
```

That route should verify ownership and set `status = "completed"` and `stage = "confirm"` when the sheet confidence is sufficient.

### Step 4: Add tests

Test `_compute_resume_path` for:

- No session -> `/discovery/{id}`
- Stage `problem` -> `/discovery/{id}`
- Stage `confirm`, no pathway -> `/pathway-review/{id}`
- Pathway `active` -> `/pathway-execute/{id}`
- Pathway `complete`, zero blocks -> `/blocks/{id}`
- Pathway `complete`, blocks > 0 -> `/exports/{id}`

## Task 4: Persist Module Pathway Completion

### Files

- Modify `backend/app/routers/modules.py`
- Modify `frontend/src/stores/modulePathwayStore.ts`
- Modify `frontend/src/pages/PathwayExecute.tsx`
- Add backend tests

### Step 1: Add backend completion helper

In `backend/app/routers/modules.py` or a service module:

```python
async def _sync_pathway_completion(project_id: uuid.UUID, db: AsyncSession) -> None:
    pw_result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = pw_result.scalar_one_or_none()
    if not pathway or not pathway.modules:
        return

    responses_result = await db.execute(
        select(ModuleResponse).where(ModuleResponse.project_id == project_id)
    )
    responses = {r.module_id: r.status for r in responses_result.scalars().all()}
    all_done = all(responses.get(mid) in {"complete", "skipped"} for mid in pathway.modules)

    if all_done:
        pathway.status = "complete"
    elif pathway.status == "complete":
        pathway.status = "active"
```

Call it after:

- module completion
- module skip

### Step 2: Return updated pathway status

When module response stream completes, include status in the `done` event:

```python
yield f"data: {json.dumps({
    'type': 'done',
    'complete': complete,
    'question_number': question_number,
    'chips': chips,
    'pathway_status': pathway.status if pathway else None,
})}\n\n"
```

For skip:

```python
return {"module_id": module_id, "status": "skipped", "pathway_status": pathway.status}
```

### Step 3: Fix frontend race

In `modulePathwayStore.ts`, call `checkCompletion` after setting pathway:

```tsx
set({ pathway: data, loading: false })
get().checkCompletion()
```

Also call it after `lockPathway` and after any response update.

In `PathwayExecute.tsx`, sequence initial loads:

```tsx
useEffect(() => {
  if (!projectId) return
  let cancelled = false

  const init = async () => {
    await fetchPathway(projectId)
    await fetchResponses(projectId)
    if (!cancelled && assembledModules.length === 0) {
      await assemble(projectId).catch(() => {})
    }
  }

  void init()
  return () => { cancelled = true }
}, [projectId])
```

If dependency lint complains, either stabilize store functions or destructure them with correct dependencies.

### Step 4: Add tests

Backend tests:

- Completing the last pending module sets `ModulePathway.status == "complete"`.
- Skipping the last pending module sets complete.
- Completing one of several modules leaves pathway active.

Frontend lint:

- Ensure hook dependencies are correct.

## Task 5: Verification

Run:

```powershell
cd frontend
npm.cmd run build
npm.cmd run lint
npm.cmd audit --json
```

Run backend syntax:

```powershell
cd backend
$env:DATABASE_URL='postgresql+asyncpg://user:pass@localhost/db'
python -m compileall app -q
```

Run backend tests after dependencies and fixtures are available:

```powershell
cd backend
python -m pytest tests -q
```

