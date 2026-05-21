# Product Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the gap between the current partial implementation and the full Ide/AI product promise described in the product report.

**Architecture:** Build only after P0 persistence, route, and authorization fixes are complete. Preserve existing FastAPI router boundaries and React page structure unless a feature is currently impossible to wire cleanly.

**Tech Stack:** React, TypeScript, Vite, Zustand, FastAPI, SQLAlchemy async, PostgreSQL, Anthropic Claude API, Clerk, Stripe.

---

## Task 1: Make Module Sessions Resumable

**Files:**
- Modify: `backend/app/routers/modules.py`
- Modify: `frontend/src/pages/ModuleSession.tsx`

- [ ] **Step 1: Change start endpoint behavior**

In `start_module`, if an active module response exists, return its messages instead of overwriting:

```python
if module_resp and module_resp.status == "active":
    messages = (module_resp.responses or {}).get("messages", [])
    return {
        "module_id": module_id,
        "label": defn["label"],
        "messages": messages,
        "question_number": sum(1 for m in messages if m.get("role") == "assistant"),
        "total_questions": 10 if mode == "deep" else 3,
        "mode": mode,
        "resumed": True,
    }
```

- [ ] **Step 2: Preserve completed transcript**

If complete:

```python
if module_resp and module_resp.status == "complete":
    return {
        "module_id": module_id,
        "label": defn["label"],
        "already_complete": True,
        "messages": (module_resp.responses or {}).get("messages", []),
        "extracted": (module_resp.responses or {}).get("extracted", {}),
    }
```

- [ ] **Step 3: Update frontend start handling**

In `ModuleSession.tsx`, after start:

```tsx
if (data.messages?.length) {
  setMessages(data.messages)
}
```

If `already_complete`, show messages and summary instead of blank completion.

## Task 2: Build Sharing Feedback UI

**Files:**
- Add: `frontend/src/components/sharing/CommentSection.tsx`
- Add: `frontend/src/components/sharing/StarRating.tsx`
- Add: `frontend/src/components/sharing/FeedbackPanel.tsx`
- Modify: `frontend/src/pages/SharedProject.tsx`
- Modify: `frontend/src/components/sharing/ShareDialog.tsx`

- [ ] **Step 1: Add comments component**

The component should:

- fetch `GET /sharing/public/{token}/comments`,
- post `POST /sharing/public/{token}/comments`,
- show author name, content, date,
- cap content length in UI before submit to match backend.

- [ ] **Step 2: Add rating component**

The component should:

- fetch `GET /sharing/public/{token}/ratings`,
- post `POST /sharing/public/{token}/ratings`,
- show average and count,
- accept name/email and 1-5 star score.

- [ ] **Step 3: Add owner feedback panel**

Owner-side Library detail should show comment count and rating average for active share. If backend lacks owner aggregate endpoint, add:

```python
GET /sharing/{project_id}/feedback
```

with ownership verification.

## Task 3: Complete Branching

**Files:**
- Modify: `backend/app/routers/branching.py`
- Add: `backend/app/services/branching_service.py`
- Modify: `frontend/src/pages/Library.tsx`

- [ ] **Step 1: Extract branch service**

Create `branching_service.py` with:

```python
async def deep_copy_project(db: AsyncSession, parent: Project, user_id: uuid.UUID, branch_name: str) -> Project:
    ...
```

Copy:

- project metadata,
- design sheet,
- discovery sessions,
- blocks,
- pipeline nodes,
- prompt kits,
- sprint plan,
- market analysis,
- module pathway,
- module responses.

Do not copy:

- external integrations,
- share links,
- comments/ratings.

- [ ] **Step 2: Add compare endpoint**

```python
@router.get("/{project_id}/compare/{branch_id}")
```

Return field-level differences across project metadata, design sheet, blocks, and pipeline.

- [ ] **Step 3: Add merge endpoint**

```python
@router.post("/{project_id}/merge/{branch_id}")
```

Start conservative: only allow merge by replacing parent project state with branch state after ownership verification. Add conflict merge UI later.

## Task 4: Complete Prompt Kit Page

**Files:**
- Add: `frontend/src/pages/PromptKit.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add route**

In `ROUTE_SUFFIX_MAP`:

```tsx
prompts: 'PromptKit',
```

In `MODULE_COMPONENTS`:

```tsx
const PromptKit = lazy(() => import('./pages/PromptKit').then(m => ({ default: m.PromptKit })))
...
PromptKit,
```

- [ ] **Step 2: Build page behavior**

PromptKit page should:

- list existing prompt kits from `GET /projects/{projectId}/prompts`,
- generate via `POST /projects/{projectId}/prompts/generate`,
- rewrite via `POST /projects/{projectId}/prompts/{prompt_id}/rewrite`,
- show latest content,
- copy all,
- copy section.

- [ ] **Step 3: Add platform selector**

Use existing platform options:

- bubble,
- webflow,
- flutterflow,
- bolt,
- lovable,
- claude-code,
- cursor,
- replit,
- generic/custom.

## Task 5: Implement Or De-scope External Integrations

**Files:**
- Modify: `backend/app/routers/integrations.py`
- Modify or add frontend integrations UI if present/needed.
- Update docs.

- [ ] **Step 1: Choose active providers**

Do not advertise six active integrations unless they actually push data. Pick one or two first, such as Notion and Trello.

- [ ] **Step 2: Add provider auth endpoints**

For each active provider:

```python
GET /integrations/{provider}/auth
POST /integrations/{provider}/callback
POST /integrations/{provider}/push/{project_id}
```

- [ ] **Step 3: Add "Coming soon" metadata**

For inactive providers, return:

```json
{ "provider": "figma", "enabled": false, "status": "coming_soon" }
```

and render disabled UI.

## Task 6: Billing Entitlement Enforcement

**Files:**
- Add: `backend/app/services/entitlement_service.py`
- Modify routers for premium features.
- Modify frontend upgrade prompts.

- [ ] **Step 1: Define plan limits**

Suggested first version:

```python
PLAN_LIMITS = {
    "free": {"projects": 3, "prompt_packages": 0, "market_analysis": 0},
    "basic": {"projects": 25, "prompt_packages": 10, "market_analysis": 5},
    "pro": {"projects": None, "prompt_packages": None, "market_analysis": None},
}
```

- [ ] **Step 2: Enforce server-side**

Apply checks before:

- project creation,
- prompt package generation,
- market analysis generation,
- sprint generation if premium,
- exports if premium.

- [ ] **Step 3: Mirror limits in frontend**

Frontend should show upgrade modal, but backend remains the source of truth.

## Task 7: Docs And Branding Cleanup

**Files:**
- Modify: `AGENTS.md`
- Modify: `CONTEXT_HANDOFF.md`
- Modify: `ARCHITECTURE.md`
- Modify: `README.md`
- Modify pathway persona files if rebrand must be complete.

- [ ] **Step 1: Update tech stack facts**

Use actual package versions:

- React 19.2.0 or updated version after dependency hardening,
- Vite 7.3.1 or updated version,
- Clerk package after migration,
- current route map.

- [ ] **Step 2: Remove stale architecture claims**

Remove references to missing stores:

- `discoveryStore`,
- `projectStore`,
- `uiStore`,

unless they are added.

- [ ] **Step 3: Rebrand remaining persona text**

Replace `ideaFORGE` with `Ide/AI` in:

- `backend/app/pathways/software_product.py`
- `backend/app/pathways/creative_writing.py`
- `backend/app/pathways/brand_identity.py`
- `backend/app/pathways/marketing_campaign.py`
- `frontend/src/pages/Settings.tsx`

## Task 8: Acceptance Criteria

- [ ] Users can resume discovery and module sessions.
- [ ] Library opens the correct next workflow step.
- [ ] Sharing works and feedback is visible.
- [ ] Branching creates usable branch projects with copied state.
- [ ] Prompt Kit page exists and uses backend routes.
- [ ] Integrations are either real or clearly marked inactive.
- [ ] Billing plans change actual feature access.
- [ ] Docs no longer contradict current code.

