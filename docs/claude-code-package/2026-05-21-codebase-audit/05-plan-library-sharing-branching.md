# Library, Sharing, Inbox, And Branching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Library a reliable project management surface by fixing broken actions, adding progress metadata, and aligning sharing/inbox/branching routes with actual backend behavior.

**Architecture:** Keep existing Library router/service boundaries. Fix immediate runtime errors first, then expand read models and route contracts. Do not redesign the whole library UI until core actions work.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL JSONB, React, TypeScript, Axios.

---

## Task 1: Fix Inbox Promotion Runtime Error

**Files:**
- Modify: `backend/app/routers/inbox.py`

- [ ] **Step 1: Replace invalid constructor keyword**

Current code uses:

```python
project = Project(
    name=payload.name or item.subject[:200],
    description=item.body or "",
    owner_id=current_user.id,
)
```

Replace with:

```python
project = Project(
    name=payload.name or item.subject[:200],
    description=item.body or "",
    user_id=current_user.id,
)
```

- [ ] **Step 2: Set sensible defaults explicitly**

Use project defaults where possible, but be explicit for fields that matter to downstream discovery:

```python
project = Project(
    name=payload.name or item.subject[:200],
    description=item.body or item.subject,
    user_id=current_user.id,
    platform="custom",
    audience="consumers",
    complexity="medium",
    tone="casual",
    pathway_id="software_product",
    ai_partner_style="strategist",
)
```

- [ ] **Step 3: Manual acceptance**

Create an inbox item from the UI, click "Start Project", and confirm navigation to `/discovery/{project_id}` works.

## Task 2: Fix Branch Creation Runtime Error

**Files:**
- Modify: `backend/app/routers/branching.py`

- [ ] **Step 1: Replace invalid constructor keyword**

Current code uses:

```python
branch_project = Project(
    name=f"{parent.name} - {payload.branch_name}",
    description=parent.description,
    owner_id=current_user.id,
)
```

Replace with:

```python
branch_project = Project(
    name=f"{parent.name} - {payload.branch_name}",
    description=parent.description,
    user_id=current_user.id,
    platform=parent.platform,
    audience=parent.audience,
    complexity=parent.complexity,
    tone=parent.tone,
    accent_color=parent.accent_color,
    pathway_id=parent.pathway_id,
    ai_partner_style=parent.ai_partner_style,
    primary_category=parent.primary_category,
    secondary_category=parent.secondary_category,
)
```

- [ ] **Step 2: Decide route compatibility**

AGENTS.md documents project-scoped branch routes, but code uses `/branching`.

Keep existing `/branching/{project_id}/branch` for backward compatibility and add aliases under `/projects/{project_id}` only if the frontend or docs need them immediately:

```python
@router.post("/{project_id}/branch", status_code=status.HTTP_201_CREATED)
async def create_branch(...):
    ...
```

If adding aliases, avoid duplicate function logic by extracting a private helper:

```python
async def _create_branch_for_project(project_id, payload, current_user, db):
    ...
```

## Task 3: Fix ShareDialog Route Mismatch

**Files:**
- Modify: `frontend/src/components/sharing/ShareDialog.tsx`

- [ ] **Step 1: Change fetch status endpoint**

Replace:

```tsx
const { data } = await apiClient.get(`/sharing/projects/${projectId}/share`)
```

With:

```tsx
const { data } = await apiClient.get(`/sharing/${projectId}/status`)
if (data.active) {
  setShareData(data)
} else {
  setShareData(null)
}
```

- [ ] **Step 2: Change create endpoint**

Replace:

```tsx
const { data } = await apiClient.post(`/sharing/projects/${projectId}/share`, {
  is_public: isPublic,
  ...(password.trim() ? { password: password.trim() } : {}),
})
```

With:

```tsx
const { data } = await apiClient.post(`/sharing/${projectId}`, {
  is_public: isPublic,
  ...(password.trim() ? { password: password.trim() } : {}),
})
```

- [ ] **Step 3: Change revoke endpoint**

Replace:

```tsx
await apiClient.delete(`/sharing/projects/${projectId}/share`)
```

With:

```tsx
await apiClient.delete(`/sharing/${projectId}`)
```

## Task 4: Add Sharing Ownership Checks

**Files:**
- Modify: `backend/app/routers/sharing.py`

- [ ] **Step 1: Add helper**

Add near the top of the file:

```python
async def _verify_project_owner(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project
```

- [ ] **Step 2: Use helper in create/status/delete**

In `create_share`, replace the inline ownership query with:

```python
await _verify_project_owner(db, project_id, current_user.id)
```

At the start of `get_share_status`, add:

```python
await _verify_project_owner(db, project_id, current_user.id)
```

At the start of `revoke_share`, add:

```python
await _verify_project_owner(db, project_id, current_user.id)
```

## Task 5: Add Feedback And Rating Toggles To Sharing

**Files:**
- Modify: `backend/app/routers/sharing.py`
- Modify: `backend/app/services/sharing_service.py`
- Modify: `frontend/src/components/sharing/ShareDialog.tsx`

- [ ] **Step 1: Extend backend request schema**

```python
class CreateShareRequest(BaseModel):
    is_public: bool = True
    password: str | None = None
    expires_hours: int | None = None
    allow_feedback: bool = True
    allow_ratings: bool = True
```

- [ ] **Step 2: Pass settings to service**

In `create_share`, add:

```python
allow_feedback=payload.allow_feedback,
allow_ratings=payload.allow_ratings,
```

- [ ] **Step 3: Extend service signature**

In `sharing_service.create_share`:

```python
async def create_share(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    is_public: bool = True,
    password: str | None = None,
    expires_hours: int | None = None,
    allow_feedback: bool = True,
    allow_ratings: bool = True,
) -> ProjectShare:
```

Set fields on the model:

```python
share = ProjectShare(
    project_id=project_id,
    share_token=secrets.token_urlsafe(32),
    is_public=is_public,
    password_hash=pw_hash,
    expires_at=expires_at,
    created_by=user_id,
    allow_feedback=allow_feedback,
    allow_ratings=allow_ratings,
)
```

- [ ] **Step 4: Add frontend toggles**

In `ShareDialog`, add state:

```tsx
const [allowFeedback, setAllowFeedback] = useState(true)
const [allowRatings, setAllowRatings] = useState(true)
```

Include in create payload:

```tsx
allow_feedback: allowFeedback,
allow_ratings: allowRatings,
```

Add two checkbox controls in the create form:

```tsx
<label className="flex items-center gap-2 text-xs text-text-muted">
  <input
    type="checkbox"
    checked={allowFeedback}
    onChange={(e) => setAllowFeedback(e.target.checked)}
  />
  Allow viewer comments
</label>
<label className="flex items-center gap-2 text-xs text-text-muted">
  <input
    type="checkbox"
    checked={allowRatings}
    onChange={(e) => setAllowRatings(e.target.checked)}
  />
  Allow star ratings
</label>
```

Style these to match existing dark glassmorphism controls after functional behavior is verified.

## Task 6: Add Library Progress Metadata

**Files:**
- Modify: `backend/app/schemas/project_snapshot.py`
- Modify: `backend/app/routers/library.py`
- Modify: `frontend/src/pages/Library.tsx`

- [ ] **Step 1: Extend `LibraryProjectRead`**

Add fields:

```python
discovery_stage: Optional[str] = None
discovery_message_count: int = 0
design_confidence: int = 0
block_count: int = 0
pathway_status: Optional[str] = None
pathway_locked: bool = False
recommended_resume_path: Optional[str] = None
```

- [ ] **Step 2: Query aggregate state in `list_library_projects`**

Add subqueries for:

- latest active session by project,
- design sheet confidence,
- block count,
- module pathway status.

If the SQL becomes too complex, keep it readable and do per-project follow-up queries first. Optimize later only if Library becomes slow.

- [ ] **Step 3: Compute recommended resume path**

Use this logic:

```python
def _recommended_resume_path(project: Project, pathway_status: str | None, confidence: int) -> str:
    if project.pathway_locked and pathway_status in {"active", "complete"}:
        return f"/pathway-execute/{project.id}"
    if confidence >= 70 and pathway_status is None:
        return f"/pathway-review/{project.id}"
    return f"/discovery/{project.id}"
```

- [ ] **Step 4: Render progress in Library**

In `LibraryProject` interface add matching fields.

Show:

- confidence percent,
- current discovery stage,
- number of messages,
- number of blocks,
- pathway status.

Change the `Open` link target from always `/discovery/${project.id}` to:

```tsx
to={project.recommended_resume_path || `/discovery/${project.id}`}
```

## Task 7: Snapshot/Version Unification Decision

**Files:**
- Modify later after explicit decision:
  - `backend/app/routers/exports.py`
  - `backend/app/routers/library.py`
  - `backend/app/services/library_service.py`
  - `frontend/src/pages/Exports.tsx`
  - `frontend/src/pages/Library.tsx`

- [ ] **Step 1: Choose `ProjectSnapshot` as canonical**

Recommended decision: keep `project_snapshots` as canonical because it captures full project state and powers Library. Deprecate `versions` or leave it read-only until migration.

- [ ] **Step 2: Change Export page Save Snapshot**

Replace:

```tsx
await apiClient.post(`/projects/${projectId}/versions/auto`)
```

With:

```tsx
await apiClient.post(`/library/${projectId}/snapshots`, {
  name: `Auto snapshot ${new Date().toLocaleString()}`,
  description: 'Saved from Export page',
})
```

- [ ] **Step 3: Extend snapshot state coverage**

Update `_gather_project_state` to include:

- `pathway_id`,
- `ai_partner_style`,
- `primary_category`,
- `secondary_category`,
- `pathway_locked`,
- prompt kits,
- sprint plan,
- module pathway,
- module responses.

Do not include shares/integrations in ordinary snapshots unless product requirements say snapshots should restore external exposure and credentials.

## Task 8: Manual Acceptance Checklist

- [ ] Inbox item can be promoted to a project.
- [ ] Branch creation no longer errors.
- [ ] Library share dialog can create, copy, show status, export CSV, and revoke.
- [ ] A user cannot get or delete another user's share status by guessing a project id.
- [ ] Library rows show progress metadata.
- [ ] Open/Resume routes to discovery, pathway review, or pathway execute based on state.
- [ ] Export page snapshot appears in Library version history if snapshot unification is implemented.

