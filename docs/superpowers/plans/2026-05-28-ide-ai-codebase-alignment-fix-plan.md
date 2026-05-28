# Ide/AI Codebase Alignment Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the current Ide/AI codebase back into alignment with the product goal: a coherent pre-builder planning pipeline that turns one rough idea into a complete, export-ready design kit.

**Architecture:** Treat v2 module responses as the canonical discovery artifact, while preserving v1 DesignSheet compatibility for template and legacy projects. Build one artifact-context layer that feeds exports, prompts, blocks, pipeline, market analysis, and sprint planning so downstream outputs use the same user knowledge that Design Kit displays.

**Tech Stack:** FastAPI, SQLAlchemy async, PostgreSQL JSONB, Clerk, Stripe, React 19, TypeScript, Vite 7, Tailwind CSS v4, Zustand, Vitest, Pytest.

---

## Audit Summary

### Product Goals

Ide/AI is trying to:

1. Let a non-technical user describe an idea and configure builder/audience/tone/complexity.
2. Run a focused AI discovery conversation that extracts structure while the user chats.
3. Convert the extracted structure into a complete design kit: module fields, feature blocks, stack/pipeline, prompt kit, sprint plan, market analysis, pitch view, and exportable files.
4. Save the work as a project with authentication, billing limits, sharing, versioning, inbox capture, and admin controls.
5. Reduce wasted credits in external builder tools by doing planning before the user opens Bubble, Cursor, Claude Code, Bolt, Lovable, Replit, etc.

### Current Alignment

The codebase has the right broad shape: Clerk auth, Stripe billing, project creation, partner styles, v2 unified Discovery, module responses, Design Kit, exports, blocks, pipeline, prompt kit, market, sprint, inbox, sharing, admin, tests, and Railway deployment files all exist.

The major issue is not absence of features. It is that v2 Discovery now writes meaningful project knowledge to `module_responses`, while several downstream systems still read the legacy `design_sheets` table. This means the Design Kit can look rich while exported design kits, blocks, prompt packages, pipeline recommendations, market analysis, and sprint plans can remain generic or incomplete.

### Highest-Risk Findings

1. **P0: v2 artifact split.** v2 writes module fields through `backend/app/services/discovery_service.py::apply_extracted_module_fields`, but exports, blocks, pipeline, prompt kit, market, and sprint still depend mostly on `DesignSheet`.
2. **P0: frontend lint fails.** `frontend/src/pages/DesignKit.tsx` calls hooks conditionally inside `FieldEditor`; `frontend/src/components/discovery/ProgressPanel.tsx` trips React 19 lint.
3. **P0: v2 Proceed gate blocks on optional fields.** The AI prompt says optional fields should not gate progress, while `Discovery.tsx` requires `overall_percent >= 100`.
4. **P0: sharing ratings are broken.** Frontend posts `{ score }`, backend requires `author_name`; frontend reads `average_score/total_ratings`, backend returns `average/count`.
5. **P1: AI-costing routes bypass entitlements.** `/pathways/detect`, prompt-package export, and prompt rewrite need consistent auth/feature gates or rate limiting.
6. **P1: auth token readiness is inconsistent.** Some raw fetch/SSE calls can proceed without a token or send `Bearer null`.
7. **P1: existing modules in v2 Design Kit can be non-actionable.** Modules like blocks, pipeline, prompt kit, market, and sprint need route/action metadata or frontend action cards.
8. **P1: deployment/docs drift.** `DEPLOYMENT_RAILWAY.md` describes an obsolete proxy topology; `AGENTS.md` is stale; backend dev dependencies are missing.

---

## File Structure

Create:
- `backend/app/services/artifact_context_service.py` - canonical v1/v2 artifact context builder.
- `frontend/src/lib/fieldValue.ts` - shared meaningful-value helper.
- `frontend/src/lib/authFetch.ts` - token-aware fetch helpers for raw fetch/SSE.
- `backend/tests/test_artifact_context.py` - service-level v1/v2 context tests.
- `backend/tests/test_entitlement_routes.py` - route-level AI-costing feature gate tests.
- `frontend/src/test/DesignKit.test.tsx` - DesignKit meaningful-value/edit flow tests.
- `frontend/src/test/sharingRatings.test.tsx` - rating contract regression tests.

Modify:
- `backend/app/routers/exports.py`
- `backend/app/services/export_service.py`
- `backend/app/routers/blocks.py`
- `backend/app/services/sheet_service.py`
- `backend/app/routers/pipeline.py`
- `backend/app/services/pipeline_service.py`
- `backend/app/routers/prompts.py`
- `backend/app/services/prompt_kit_service.py`
- `backend/app/routers/market.py`
- `backend/app/services/market_service.py`
- `backend/app/routers/sprints.py`
- `backend/app/services/sprint_service.py`
- `backend/app/routers/pathways.py`
- `backend/app/routers/sharing.py`
- `backend/app/routers/modules.py`
- `backend/app/schemas/project.py`
- `frontend/src/pages/Discovery.tsx`
- `frontend/src/pages/DesignKit.tsx`
- `frontend/src/components/discovery/ProgressPanel.tsx`
- `frontend/src/components/sharing/FeedbackPanel.tsx`
- `frontend/src/components/sharing/StarRating.tsx`
- `frontend/src/lib/apiClient.ts`
- `frontend/src/stores/inboxStore.ts`
- `frontend/src/pages/SprintPlanner.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/Inbox.tsx`
- `frontend/src/components/layout/Sidebar.tsx` callers where project id is missing.
- `backend/pyproject.toml`
- `docker-compose.yml`
- `DEPLOYMENT_RAILWAY.md`
- `AGENTS.md`
- `CONTEXT_HANDOFF.md`
- `TODO.md`
- `CHANGELOG.md`

---

### Task 1: Fix Frontend Lint Blockers

**Files:**
- Modify: `frontend/src/pages/DesignKit.tsx`
- Modify: `frontend/src/components/discovery/ProgressPanel.tsx`
- Test: `frontend/src/test/DesignKit.test.tsx`

- [ ] **Step 1: Write a failing DesignKit hook/field test**

Create `frontend/src/test/DesignKit.test.tsx`:

```tsx
import { describe, expect, it } from 'vitest'

function hasMeaningfulValue(value: unknown): boolean {
  if (value === undefined || value === null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
  return true
}

describe('DesignKit field completion semantics', () => {
  it('does not count empty arrays, objects, or whitespace as filled', () => {
    expect(hasMeaningfulValue('')).toBe(false)
    expect(hasMeaningfulValue('   ')).toBe(false)
    expect(hasMeaningfulValue([])).toBe(false)
    expect(hasMeaningfulValue({})).toBe(false)
    expect(hasMeaningfulValue(['one'])).toBe(true)
    expect(hasMeaningfulValue({ key: 'value' })).toBe(true)
  })
})
```

- [ ] **Step 2: Run lint to confirm the current blocker**

Run:

```powershell
cd frontend
npm.cmd run lint
```

Expected: FAIL with `react-hooks/rules-of-hooks` in `DesignKit.tsx` and `react-hooks/set-state-in-effect` in `ProgressPanel.tsx`.

- [ ] **Step 3: Split conditional hook branches into stable child components**

In `frontend/src/pages/DesignKit.tsx`, replace the conditional `useState` calls inside `FieldEditor` with child components:

```tsx
function ListFieldEditor({ field, items, onChange }: {
  field: FieldSchema
  items: unknown[]
  onChange: (v: unknown) => void
}) {
  const [inputVal, setInputVal] = useState('')
  const addItem = () => {
    const trimmed = inputVal.trim()
    if (!trimmed) return
    onChange([...items, trimmed])
    setInputVal('')
  }
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] text-text-muted font-medium">
        {field.label}{field.required && <span className="text-amber-300 ml-0.5">*</span>}
      </label>
      <div className="flex flex-wrap gap-1.5 mb-1">
        {items.map((item, i) => (
          <span key={i} className="inline-flex items-center gap-1 text-[11px] bg-accent/10 border border-accent/20 text-accent/90 rounded px-2 py-0.5">
            {String(item)}
            <button type="button" onClick={() => onChange(items.filter((_, idx) => idx !== i))} className="text-accent/50 hover:text-accent">x</button>
          </span>
        ))}
      </div>
      <div className="flex gap-1.5">
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addItem() } }}
          placeholder={`Add ${field.label.toLowerCase()}...`}
          className="flex-1 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent/40"
        />
        <button type="button" onClick={addItem} className="text-xs text-accent hover:bg-accent/10 px-2 py-1.5 rounded border border-accent/30">+</button>
      </div>
    </div>
  )
}

function DictFieldEditor({ field, dict, onChange }: {
  field: FieldSchema
  dict: Record<string, unknown>
  onChange: (v: unknown) => void
}) {
  const [newKey, setNewKey] = useState('')
  const [newVal, setNewVal] = useState('')
  const addEntry = () => {
    const k = newKey.trim()
    const v = newVal.trim()
    if (!k || !v) return
    onChange({ ...dict, [k]: v })
    setNewKey('')
    setNewVal('')
  }
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] text-text-muted font-medium">
        {field.label}{field.required && <span className="text-amber-300 ml-0.5">*</span>}
      </label>
      {Object.entries(dict).map(([k, v]) => (
        <div key={k} className="flex gap-1.5">
          <input className="w-1/3 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white" value={k} readOnly />
          <input
            className="flex-1 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white"
            value={String(v)}
            onChange={(e) => onChange({ ...dict, [k]: e.target.value })}
          />
          <button type="button" onClick={() => {
            const next = { ...dict }
            delete next[k]
            onChange(next)
          }} className="text-xs text-red-300 px-2">x</button>
        </div>
      ))}
      <div className="flex gap-1.5">
        <input value={newKey} onChange={(e) => setNewKey(e.target.value)} placeholder="Key" className="w-1/3 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white" />
        <input value={newVal} onChange={(e) => setNewVal(e.target.value)} placeholder="Value" className="flex-1 bg-white/[0.04] border border-border rounded px-2 py-1.5 text-xs text-white" />
        <button type="button" onClick={addEntry} className="text-xs text-accent hover:bg-accent/10 px-2 py-1.5 rounded border border-accent/30">+</button>
      </div>
    </div>
  )
}
```

Then keep `FieldEditor` hook-free:

```tsx
function FieldEditor({ field, value, onChange }: {
  field: FieldSchema
  value: unknown
  onChange: (v: unknown) => void
}) {
  if (field.type === 'list') {
    return <ListFieldEditor field={field} items={Array.isArray(value) ? value : []} onChange={onChange} />
  }
  if (field.type === 'dict') {
    const dict = typeof value === 'object' && value && !Array.isArray(value)
      ? value as Record<string, unknown>
      : {}
    return <DictFieldEditor field={field} dict={dict} onChange={onChange} />
  }
  if (field.type === 'longtext') {
    return (
      <div className="flex flex-col gap-1">
        <label className="text-[11px] text-text-muted font-medium">
          {field.label}{field.required && <span className="text-amber-300 ml-0.5">*</span>}
        </label>
        <textarea
          value={typeof value === 'string' ? value : ''}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          className="bg-white/[0.04] border border-border rounded-lg px-3 py-2 text-xs text-white resize-y focus:outline-none focus:ring-1 focus:ring-accent/40"
          placeholder={field.extraction_hint || `Enter ${field.label.toLowerCase()}...`}
        />
      </div>
    )
  }
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] text-text-muted font-medium">
        {field.label}{field.required && <span className="text-amber-300 ml-0.5">*</span>}
      </label>
      <input
        type="text"
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.target.value)}
        className="bg-white/[0.04] border border-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:ring-1 focus:ring-accent/40"
        placeholder={field.extraction_hint || `Enter ${field.label.toLowerCase()}...`}
      />
    </div>
  )
}
```

- [ ] **Step 4: Fix ProgressPanel lint without removing behavior**

In `frontend/src/components/discovery/ProgressPanel.tsx`, replace the synchronous effect state update with a microtask callback:

```tsx
useEffect(() => {
  if (!recentModuleId) return
  queueMicrotask(() => {
    setExpanded((prev) => {
      if (prev.has(recentModuleId)) return prev
      const next = new Set(prev)
      next.add(recentModuleId)
      while (next.size > MAX_AUTO_EXPANDED) {
        const oldest = next.values().next().value
        if (!oldest) break
        next.delete(oldest)
      }
      return next
    })
  })
}, [recentModuleId])
```

- [ ] **Step 5: Verify**

Run:

```powershell
cd frontend
npm.cmd run lint
npx.cmd tsc -b --noEmit
npm.cmd test
```

Expected: lint passes, TypeScript passes, 31+ tests pass.

---

### Task 2: Add Shared Meaningful-Value Semantics

**Files:**
- Create: `frontend/src/lib/fieldValue.ts`
- Modify: `frontend/src/pages/DesignKit.tsx`
- Modify: `frontend/src/pages/Discovery.tsx`
- Test: `frontend/src/test/DesignKit.test.tsx`

- [ ] **Step 1: Create helper**

Create `frontend/src/lib/fieldValue.ts`:

```ts
export function hasMeaningfulValue(value: unknown): boolean {
  if (value === undefined || value === null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  if (typeof value === 'object') return Object.keys(value as Record<string, unknown>).length > 0
  return true
}
```

- [ ] **Step 2: Use helper in DesignKit**

In `frontend/src/pages/DesignKit.tsx`:

```tsx
import { hasMeaningfulValue } from '../lib/fieldValue'

const filledCount = mod.fields.filter((f) => hasMeaningfulValue(mod.responses[f.key])).length

const totalFilled = data.modules.reduce(
  (sum, m) => sum + m.fields.filter((f) => hasMeaningfulValue(m.responses[f.key])).length,
  0,
)

const unfilledModules = data.modules.filter((m) => {
  const requiredFields = m.fields.filter((f) => f.required)
  return requiredFields.some((f) => !hasMeaningfulValue(m.responses[f.key]))
})
```

- [ ] **Step 3: Change v2 Proceed gate to required fields**

In `frontend/src/pages/Discovery.tsx`, replace:

```tsx
const pct = fieldSummary.overall_percent
const ready = pct >= 100
```

with:

```tsx
const requiredReady =
  fieldSummary.required_total === 0 ||
  fieldSummary.required_filled >= fieldSummary.required_total
const ready = scopeModuleIds ? true : requiredReady
const pct = fieldSummary.required_total > 0
  ? Math.round((fieldSummary.required_filled / fieldSummary.required_total) * 100)
  : fieldSummary.overall_percent
```

Keep optional completion visible in `ProgressPanel`; do not make optional fields block the main CTA.

- [ ] **Step 4: Verify**

Run:

```powershell
cd frontend
npm.cmd test -- DesignKit.test.tsx
npx.cmd tsc -b --noEmit
```

Expected: new helper tests pass and TypeScript passes.

---

### Task 3: Build Canonical Artifact Context

**Files:**
- Create: `backend/app/services/artifact_context_service.py`
- Test: `backend/tests/test_artifact_context.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_artifact_context.py`:

```python
import uuid
import pytest

from app.models.project import Project
from app.models.design_sheet import DesignSheet
from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.services.artifact_context_service import build_artifact_context


@pytest.mark.asyncio
async def test_v2_context_uses_module_responses(async_session):
    project = Project(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Clinic booking app",
        description="Book appointments for local clinics",
        platform="claude-code",
        audience="businesses",
        complexity="medium",
        tone="technical",
        pathway_id="software_product",
        primary_category="software",
        flow_version="v2",
    )
    async_session.add(project)
    await async_session.flush()

    async_session.add(ModulePathway(
        project_id=project.id,
        modules=["problem_definition"],
        status="active",
    ))
    async_session.add(ModuleResponse(
        project_id=project.id,
        module_id="problem_definition",
        responses={
            "problem_statement": "Small clinics lose bookings by phone.",
            "target_users": ["clinic admins"],
        },
        status="active",
    ))
    await async_session.flush()

    ctx = await build_artifact_context(async_session, project.id, project.user_id)

    assert ctx["flow_version"] == "v2"
    assert "Small clinics lose bookings by phone." in ctx["discovery_summary"]
    assert ctx["modules"][0]["module_id"] == "problem_definition"
    assert ctx["modules"][0]["responses"]["target_users"] == ["clinic admins"]


@pytest.mark.asyncio
async def test_v1_context_uses_design_sheet(async_session):
    project = Project(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Legacy app",
        description="Legacy flow",
        flow_version="v1",
    )
    async_session.add(project)
    await async_session.flush()
    async_session.add(DesignSheet(
        project_id=project.id,
        problem="Legacy problem",
        audience="Legacy audience",
        mvp="Legacy MVP",
        platform="custom",
        tone="casual",
        confidence_score=70,
    ))
    await async_session.flush()

    ctx = await build_artifact_context(async_session, project.id, project.user_id)

    assert ctx["flow_version"] == "v1"
    assert ctx["problem"] == "Legacy problem"
    assert ctx["audience"] == "Legacy audience"
```

- [ ] **Step 2: Run tests to verify missing service**

Run:

```powershell
cd backend
python -m pytest tests/test_artifact_context.py -q
```

Expected: FAIL because `artifact_context_service` does not exist.

- [ ] **Step 3: Implement service**

Create `backend/app/services/artifact_context_service.py`:

```python
from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.models.design_sheet import DesignSheet
from app.models.module_response import ModuleResponse
from app.models.pipeline_node import PipelineNode
from app.models.project import Project
from app.services.discovery_service import load_decorated_pathway_modules


def _value_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _module_summary(modules: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for mod in modules:
        label = mod.get("label") or mod.get("module_id")
        responses = mod.get("responses") or {}
        if not responses:
            continue
        lines.append(f"## {label}")
        fields = {f.get("key"): f for f in mod.get("fields", []) if f.get("key")}
        for key, value in responses.items():
            if key.startswith("__"):
                continue
            text = _value_text(value)
            if not text:
                continue
            field = fields.get(key, {})
            lines.append(f"- {field.get('label') or key}: {text}")
    return "\n".join(lines)


async def build_artifact_context(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    project_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    sheet_result = await db.execute(select(DesignSheet).where(DesignSheet.project_id == project_id))
    sheet = sheet_result.scalar_one_or_none()

    blocks_result = await db.execute(select(Block).where(Block.project_id == project_id).order_by(Block.order))
    blocks = list(blocks_result.scalars().all())

    pipeline_result = await db.execute(select(PipelineNode).where(PipelineNode.project_id == project_id))
    pipeline = list(pipeline_result.scalars().all())

    context: dict[str, Any] = {
        "project": project,
        "sheet": sheet,
        "blocks": blocks,
        "pipeline": pipeline,
        "flow_version": getattr(project, "flow_version", "v1"),
        "project_name": project.name,
        "project_description": project.description or "",
        "platform": project.platform or (sheet.platform if sheet else "custom"),
        "audience": project.audience or (sheet.audience if sheet else ""),
        "tone": project.tone or (sheet.tone if sheet else ""),
        "complexity": project.complexity or "medium",
        "problem": sheet.problem if sheet else "",
        "mvp": sheet.mvp if sheet else "",
        "features": sheet.features if sheet else [],
        "tech_constraints": sheet.tech_constraints if sheet else "",
        "success_metric": sheet.success_metric if sheet else "",
        "confidence_score": sheet.confidence_score if sheet else 0,
        "modules": [],
        "discovery_summary": "",
    }

    if getattr(project, "flow_version", "v1") == "v2":
        decorated = await load_decorated_pathway_modules(db, project_id)
        response_result = await db.execute(
            select(ModuleResponse).where(ModuleResponse.project_id == project_id)
        )
        responses = {r.module_id: r for r in response_result.scalars().all()}
        modules = []
        for mod in decorated:
            response = responses.get(mod["module_id"])
            modules.append({
                **mod,
                "responses": dict(response.responses or {}) if response else {},
                "status": response.status if response else "pending",
            })
        context["modules"] = modules
        context["discovery_summary"] = _module_summary(modules)
        if not context["problem"]:
            context["problem"] = context["discovery_summary"]

    return context
```

- [ ] **Step 4: Verify**

Run:

```powershell
cd backend
python -m pytest tests/test_artifact_context.py -q
```

Expected: PASS.

---

### Task 4: Feed v2 Context Into Exports and Prompt Packages

**Files:**
- Modify: `backend/app/routers/exports.py`
- Modify: `backend/app/services/export_service.py`
- Modify: `backend/app/services/prompt_package_service.py`
- Test: `backend/tests/test_artifact_context.py`

- [ ] **Step 1: Extend export service with context-based generators**

Add to `backend/app/services/export_service.py`:

```python
async def generate_markdown_from_context(context: dict) -> str:
    if context.get("flow_version") != "v2":
        return await generate_markdown(context["sheet"], context["blocks"], context["pipeline"])
    lines = [
        f"# {context['project_name']} Design Kit",
        "",
        "## Project",
        context.get("project_description") or "Not specified",
        "",
        "## Discovery Summary",
        context.get("discovery_summary") or "No module responses captured yet.",
        "",
        "## Module Details",
    ]
    for mod in context.get("modules", []):
        lines.append(f"### {mod.get('label', mod.get('module_id'))}")
        responses = mod.get("responses") or {}
        for field in mod.get("fields", []):
            key = field.get("key")
            value = responses.get(key)
            if value in (None, "", [], {}):
                continue
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            lines.append(f"- **{field.get('label', key)}:** {value}")
        generated = responses.get("__generated_output")
        if isinstance(generated, dict) and generated.get("content"):
            lines.extend(["", generated["content"]])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


async def generate_text_from_context(context: dict) -> str:
    markdown = await generate_markdown_from_context(context)
    return markdown.replace("# ", "").replace("## ", "").replace("### ", "").replace("**", "")
```

- [ ] **Step 2: Update export route**

In `backend/app/routers/exports.py`, import and use the new context builder:

```python
from app.services.artifact_context_service import build_artifact_context

context = await build_artifact_context(db, project_id, current_user.id)
if context["flow_version"] == "v2":
    if format == "md":
        content = await export_service.generate_markdown_from_context(context)
    elif format == "txt":
        content = await export_service.generate_text_from_context(context)
    else:
        content = await generators[format](context["sheet"], context["blocks"], context["pipeline"])
else:
    project, sheet, blocks, pipeline = await _get_project_data(project_id, current_user.id, db)
    content = await generators[format](sheet, blocks, pipeline)
```

Keep PDF/DOCX on the old sheet-backed path initially if converting rich v2 context would enlarge the patch too much. The first release must fix MD/TXT/ZIP prompt truth; PDF/DOCX can call `generate_text_from_context` in a second pass.

- [ ] **Step 3: Update prompt package route to use v2 summary**

In `backend/app/routers/exports.py`, replace manual `project_data` construction with `context = await build_artifact_context(...)`, then pass:

```python
project_data = {
    "project_name": context["project_name"],
    "project_description": context["project_description"],
    "problem": context["problem"] or context["discovery_summary"] or "Not specified",
    "audience": context["audience"] or "Not specified",
    "mvp": context["mvp"] or "Derived from module responses",
    "features": context["features"] or [],
    "tone": context["tone"] or "Not specified",
    "platform": context["platform"] or "Not specified",
    "tech_constraints": context["tech_constraints"] or "None",
    "success_metric": context["success_metric"] or "Not specified",
    "confidence_score": context["confidence_score"],
    "modules": context["modules"],
    "discovery_summary": context["discovery_summary"],
    "blocks": [
        {"name": b.name, "description": b.description or "", "category": b.category, "priority": b.priority, "effort": b.effort, "is_mvp": b.is_mvp}
        for b in context["blocks"]
    ],
    "pipeline": [{"layer": n.layer, "tool": n.selected_tool} for n in context["pipeline"]],
    "market_analysis": {},
}
```

- [ ] **Step 4: Verify**

Run:

```powershell
cd backend
python -m pytest tests/test_artifact_context.py tests/test_chips_and_exports.py -q
```

Expected: context tests pass; existing export slug/transcript tests remain green.

---

### Task 5: Feed v2 Context Into Blocks, Pipeline, PromptKit, Market, and Sprint

**Files:**
- Modify: `backend/app/routers/blocks.py`
- Modify: `backend/app/services/sheet_service.py`
- Modify: `backend/app/routers/pipeline.py`
- Modify: `backend/app/services/pipeline_service.py`
- Modify: `backend/app/routers/prompts.py`
- Modify: `backend/app/services/prompt_kit_service.py`
- Modify: `backend/app/services/market_service.py`
- Modify: `backend/app/services/sprint_service.py`
- Test: `backend/tests/test_artifact_context.py`

- [ ] **Step 1: Add context text helper**

In `backend/app/services/artifact_context_service.py`:

```python
def context_for_ai(context: dict[str, Any]) -> str:
    parts = [
        f"Project: {context.get('project_name', '')}",
        f"Description: {context.get('project_description', '')}",
        f"Platform: {context.get('platform', '')}",
        f"Audience: {context.get('audience', '')}",
        f"Tone: {context.get('tone', '')}",
        "",
        context.get("discovery_summary") or "",
    ]
    return "\n".join(p for p in parts if p is not None).strip()
```

- [ ] **Step 2: Add block generation from context**

In `backend/app/services/sheet_service.py`:

```python
async def generate_blocks_from_context(
    db: AsyncSession,
    context: dict,
    project_id: uuid.UUID,
    pathway: PathwayConfig | None = None,
) -> list[Block]:
    pw = _get_pathway(pathway)
    valid_categories = {c.id for c in pw.block_categories}
    default_category = pw.block_categories[0].id if pw.block_categories else "core"
    prompt = f"""Generate 8-12 feature blocks from this Ide/AI design-kit context.

{context.get("discovery_summary") or context.get("problem") or context.get("project_description")}

Return JSON array of objects with name, description, category, priority, effort.
Valid categories: {sorted(valid_categories)}
Priority values: {pw.block_priorities}
Effort values: {pw.block_efforts}
"""
    response = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2048,
        system="You are a product feature generator. Return only valid JSON arrays.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        block_data = json.loads(text)
    except json.JSONDecodeError:
        block_data = []
    blocks = []
    for i, bd in enumerate(block_data):
        cat = bd.get("category", default_category)
        if cat not in valid_categories:
            cat = default_category
        priority = bd.get("priority", pw.block_priorities[0] if pw.block_priorities else "mvp")
        block = Block(
            project_id=project_id,
            name=bd.get("name", f"Feature {i + 1}"),
            description=bd.get("description", ""),
            category=cat,
            priority=priority,
            effort=bd.get("effort", pw.block_efforts[1] if len(pw.block_efforts) > 1 else "M"),
            order=i,
            is_mvp=priority == (pw.block_priorities[0] if pw.block_priorities else "mvp"),
        )
        db.add(block)
        blocks.append(block)
    await db.flush()
    return blocks
```

- [ ] **Step 3: Route v2 block generation through context**

In `backend/app/routers/blocks.py`:

```python
from app.services.artifact_context_service import build_artifact_context
from app.services.sheet_service import generate_blocks, generate_blocks_from_context

context = await build_artifact_context(db, project_id, current_user.id)
if context["flow_version"] == "v2":
    blocks = await generate_blocks_from_context(db, context, project_id, pathway=pw)
else:
    blocks = await generate_blocks(db, sheet, project_id, pathway=pw)
```

- [ ] **Step 4: Apply same context pattern to pipeline, prompts, market, and sprint**

For each generator, preserve existing v1 behavior and add v2 prompt context:

```python
context = await build_artifact_context(db, project_id, current_user.id)
if context["flow_version"] == "v2":
    source_text = context_for_ai(context)
else:
    source_text = legacy_design_sheet_text
```

Use `source_text` in prompts instead of empty `DesignSheet` values.

- [ ] **Step 5: Verify**

Run:

```powershell
cd backend
python -m pytest tests/test_artifact_context.py -q
```

Expected: v2 context remains stable and no v1 behavior regresses.

---

### Task 6: Make v2 Existing Modules Actionable

**Files:**
- Modify: `frontend/src/pages/DesignKit.tsx`
- Modify: `backend/app/services/modular_pathway_service.py`

- [ ] **Step 1: Add action map**

In `frontend/src/pages/DesignKit.tsx`:

```tsx
const MODULE_ACTIONS: Record<string, { label: string; path: (projectId: string) => string }> = {
  design_blocks_board: { label: 'Open Blocks', path: (id) => `/blocks/${id}` },
  pipeline_builder: { label: 'Open Pipeline', path: (id) => `/pipeline/${id}` },
  prompt_kit_generator: { label: 'Open Prompts', path: (id) => `/prompts/${id}` },
  market_analysis: { label: 'Open Market Analysis', path: (id) => `/market/${id}` },
  sprint_planner: { label: 'Open Sprint Planner', path: (id) => `/sprints/${id}` },
  pitch_mode: { label: 'Open Pitch Mode', path: (id) => `/pitch/${id}` },
  export_center: { label: 'Open Exports', path: (id) => `/exports/${id}` },
}
```

Render the action in `ModuleCard`:

```tsx
const action = projectId ? MODULE_ACTIONS[mod.module_id] : null
{action && (
  <button
    type="button"
    onClick={() => navigate(action.path(projectId))}
    className="text-xs font-medium text-accent border border-accent/30 hover:bg-accent/10 px-3 py-2 rounded-lg transition-colors"
  >
    {action.label}
  </button>
)}
```

- [ ] **Step 2: Pass `projectId` and `navigate` into ModuleCard**

Update the component props and call site:

```tsx
<ModuleCard
  key={mod.module_id}
  mod={mod}
  projectId={projectId}
  onSave={handleSave}
  onRefreshOutput={handleRefreshOutput}
/>
```

- [ ] **Step 3: Verify**

Run:

```powershell
cd frontend
npx.cmd tsc -b --noEmit
```

Expected: TypeScript passes.

---

### Task 7: Fix Sharing Rating Contract

**Files:**
- Modify: `backend/app/routers/sharing.py`
- Modify: `frontend/src/components/sharing/FeedbackPanel.tsx`
- Modify: `frontend/src/components/sharing/StarRating.tsx`
- Test: `frontend/src/test/sharingRatings.test.tsx`

- [ ] **Step 1: Relax anonymous rating author requirement**

In `backend/app/routers/sharing.py`:

```python
class RatingCreate(BaseModel):
    author_name: str = Field(default="Anonymous", min_length=1, max_length=100)
    author_email: Optional[str] = Field(None, max_length=255)
    score: float = Field(ge=0, le=5)
```

- [ ] **Step 2: Return frontend-compatible keys**

In `get_ratings`, return both old and new keys for compatibility:

```python
count = row.count or 0
average = round(float(row.average), 1) if row.average else 0
return {
    "count": count,
    "average": average,
    "total_ratings": count,
    "average_score": average,
}
```

- [ ] **Step 3: Update frontend to accept either key set**

In `FeedbackPanel.tsx`:

```tsx
setAverageScore(data.average_score ?? data.average ?? 0)
setTotalRatings(data.total_ratings ?? data.count ?? 0)
```

In `StarRating.tsx`, either keep `{ score }` after backend relaxation or send:

```tsx
body: JSON.stringify({ score, author_name: 'Anonymous' }),
```

- [ ] **Step 4: Verify**

Run:

```powershell
cd frontend
npm.cmd test
```

Expected: sharing rating regression test passes.

---

### Task 8: Centralize Token-Aware Fetch/SSE

**Files:**
- Create: `frontend/src/lib/authFetch.ts`
- Modify: `frontend/src/lib/apiClient.ts`
- Modify: `frontend/src/hooks/useSSE.ts`
- Modify: `frontend/src/stores/inboxStore.ts`
- Modify: `frontend/src/pages/SprintPlanner.tsx`

- [ ] **Step 1: Add helper**

Create `frontend/src/lib/authFetch.ts`:

```ts
import { getAuthToken } from './apiClient'

export async function authFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const token = await getAuthToken()
  if (!token) throw new Error('Authentication is not ready')
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${token}`)
  return fetch(input, { ...init, headers })
}

export async function optionalAuthHeaders(): Promise<Record<string, string>> {
  const token = await getAuthToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
```

- [ ] **Step 2: Use helper in SprintPlanner**

Replace raw header construction:

```tsx
const response = await authFetch(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
})
```

- [ ] **Step 3: Let inbox retry when token is not ready**

In `inboxStore.ts`, replace:

```ts
if (!token) {
  scheduleReconnect = false
  return
}
```

with:

```ts
if (!token) {
  throw new Error('Auth token not ready')
}
```

This keeps the existing exponential reconnect path active.

- [ ] **Step 4: Verify**

Run:

```powershell
cd frontend
npm.cmd test
npx.cmd tsc -b --noEmit
```

Expected: tests and TS pass.

---

### Task 9: Gate AI-Costing Backend Routes

**Files:**
- Modify: `backend/app/routers/pathways.py`
- Modify: `backend/app/routers/exports.py`
- Modify: `backend/app/routers/prompts.py`
- Modify: `backend/app/schemas/project.py`
- Test: `backend/tests/test_entitlement_routes.py`

- [ ] **Step 1: Add route tests for prompt-package limits**

Create `backend/tests/test_entitlement_routes.py`:

```python
def test_prompt_package_export_rejects_free_plan(client, auth_headers, project_factory):
    project = project_factory(account_type="free")
    response = client.post(
        f"/api/v1/projects/{project.id}/export/prompt-package",
        json={"platform": "cursor"},
        headers=auth_headers(project.user),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "feature_limit_reached"
```

- [ ] **Step 2: Gate prompt package export**

In `backend/app/routers/exports.py`:

```python
from app.services.entitlement_service import require_feature_usage

await require_feature_usage(current_user, db, "prompt_packages")
```

Place it at the start of `export_prompt_package`.

- [ ] **Step 3: Gate prompt rewrite**

In `backend/app/routers/prompts.py`, add:

```python
await require_feature_usage(current_user, db, "prompt_packages")
```

at the start of `rewrite_prompt`.

- [ ] **Step 4: Authenticate pathway detection**

In `backend/app/routers/pathways.py`, change the endpoint signature:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.routers.auth import get_current_user

@router.post("/detect")
async def detect_pathway_endpoint(
    payload: DetectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await detect_pathway(payload.description)
```

If public detection is ever needed on landing pages, add a separate rate-limited endpoint later; do not leave the AI-calling endpoint open.

- [ ] **Step 5: Validate AI partner styles on project writes**

In `backend/app/schemas/project.py`:

```python
from pydantic import field_validator
from app.services.partner_style_service import validate_partner_style

@field_validator("ai_partner_style")
@classmethod
def validate_ai_partner_style(cls, value: str) -> str:
    return validate_partner_style(value)
```

Add this validator to both create and update schemas where the field is accepted.

- [ ] **Step 6: Verify**

Run:

```powershell
cd backend
python -m pytest tests/test_entitlements.py tests/test_partner_style.py tests/test_entitlement_routes.py -q
```

Expected: route gates reject free-plan prompt package generation; partner style route validation passes.

---

### Task 10: Validate Project Pathway Membership for Module Updates

**Files:**
- Modify: `backend/app/routers/modules.py`
- Modify: `backend/app/routers/module_pathway.py`
- Test: `backend/tests/test_discovery_v2_integration.py`

- [ ] **Step 1: Add helper**

In `backend/app/routers/modules.py`:

```python
async def _ensure_module_in_project_pathway(
    project_id: uuid.UUID,
    module_id: str,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = result.scalar_one_or_none()
    modules = set(pathway.modules or []) if pathway else set()
    if module_id not in modules:
        raise HTTPException(status_code=404, detail="Module is not part of this project pathway")
```

- [ ] **Step 2: Call helper in write/action endpoints**

Call `_ensure_module_in_project_pathway(project_id, module_id, db)` before:
- `start_module`
- `respond_module`
- `skip_module`
- `update_module_responses`
- `refresh_module_output`

- [ ] **Step 3: Verify**

Add a regression test that a valid global module ID outside the pathway returns 404, then run:

```powershell
cd backend
python -m pytest tests/test_discovery_v2_integration.py -q
```

Expected: outside-pathway module writes are rejected.

---

### Task 11: Billing State Hardening

**Files:**
- Modify: `backend/app/models/user.py`
- Create: new Alembic migration after `031`
- Modify: `backend/app/routers/billing.py`
- Test: `backend/tests/test_billing.py`

- [ ] **Step 1: Add subscription columns**

Add to `User`:

```python
stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
subscription_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
subscription_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
subscription_current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

- [ ] **Step 2: Create migration**

Run:

```powershell
cd backend
alembic revision -m "add stripe subscription state"
```

Migration body:

```python
def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("subscription_status", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("subscription_price_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("subscription_current_period_end", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_users_stripe_subscription_id", "users", ["stripe_subscription_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_stripe_subscription_id", "users", type_="unique")
    op.drop_column("users", "subscription_current_period_end")
    op.drop_column("users", "subscription_price_id")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
```

- [ ] **Step 3: Reuse existing customer in checkout**

In `billing.py`, use:

```python
checkout_kwargs = {
    "mode": "subscription",
    "payment_method_types": ["card"],
    "line_items": [{"price": stripe_price, "quantity": 1}],
    "client_reference_id": str(current_user.id),
    "success_url": f"{settings.FRONTEND_URL}/home?billing=success",
    "cancel_url": f"{settings.FRONTEND_URL}/pricing",
    "metadata": {"user_id": str(current_user.id), "price_id": payload.price_id},
}
if current_user.stripe_customer_id:
    checkout_kwargs["customer"] = current_user.stripe_customer_id
else:
    checkout_kwargs["customer_email"] = current_user.email
session = stripe.checkout.Session.create(**checkout_kwargs)
```

- [ ] **Step 4: Persist subscription lifecycle**

For `checkout.session.completed` and `customer.subscription.updated/deleted`, update the new columns from Stripe payload. Use idempotent `update(User).where(...)`.

- [ ] **Step 5: Verify**

Run:

```powershell
cd backend
python -m pytest tests/test_billing.py -q
```

Expected: checkout reuses customer, webhook stores subscription state, deleted subscription downgrades account to free.

---

### Task 12: Fix Deployment, Dev Dependency, and Source-of-Truth Drift

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `docker-compose.yml`
- Modify: `DEPLOYMENT_RAILWAY.md`
- Modify: `AGENTS.md`
- Modify: `CONTEXT_HANDOFF.md`
- Modify: `TODO.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add backend dev dependencies**

In `backend/pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0,<9.0.0",
    "pytest-asyncio>=0.23.0,<1.0.0",
    "aiosqlite>=0.20.0,<1.0.0",
    "httpx>=0.28.1,<0.29.0"
]
```

- [ ] **Step 2: Fix docker-compose frontend service**

Either remove the incorrect `command: npm run dev` from the Caddy image, or create a separate dev override. Production-style compose should be:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  ports:
    - "5173:80"
  depends_on:
    - backend
```

- [ ] **Step 3: Rewrite Railway docs for actual topology**

Document:
- Two Railway services: backend and frontend.
- No reverse proxy.
- `VITE_API_BASE_URL` must be the public backend URL plus `/api/v1`, for example `https://backend-production-9c212.up.railway.app/api/v1`.
- Required frontend var: `VITE_CLERK_PUBLISHABLE_KEY`.
- Required backend vars: `DATABASE_URL`, `ANTHROPIC_KEY`, `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, Stripe price IDs, `FRONTEND_URL`, `INBOX_DOMAIN`.
- Recommended production hardening vars: `CORS_ORIGINS`, `CLERK_ISSUER`, `CLERK_AUTHORIZED_PARTIES`, `RESEND_WEBHOOK_SECRET`, `REDIS_URL`, `SHARE_ACCESS_SECRET`, `INTEGRATION_TOKEN_KEY`.

- [ ] **Step 4: Refresh AGENTS.md**

Update:
- Working directory to `C:\Users\vybec\OneDrive\Documents\Development\Ide_AI`.
- Frontend stack to React 19.2 and Vite 7.3.
- Migration list through 031.
- Module count to 40 if documenting actual seed file.
- Template count to 160 if documenting actual seed file.

- [ ] **Step 5: Verify**

Run:

```powershell
git diff --check
cd frontend
npm.cmd test
npx.cmd tsc -b --noEmit
cd ..\backend
python -m pytest tests/ -q -k "not PromptComposition"
```

Expected: no whitespace errors; frontend tests pass; TypeScript passes; backend tests run once dev dependencies are installed.

---

## Implementation Order

1. Task 1: lint blockers.
2. Task 2: meaningful-value and Proceed gate semantics.
3. Task 3: artifact context service.
4. Task 4: exports and prompt packages use v2 context.
5. Task 5: blocks/pipeline/prompts/market/sprint use v2 context.
6. Task 6: DesignKit action cards for existing modules.
7. Task 7: sharing rating contract.
8. Task 8: token-aware fetch/SSE helpers.
9. Task 9: AI route entitlement gates and partner validation.
10. Task 10: module membership validation.
11. Task 11: billing state hardening.
12. Task 12: docs, deployment, and test reproducibility.

Commit after each task using conventional commits, for example:

```powershell
git add frontend/src/pages/DesignKit.tsx frontend/src/components/discovery/ProgressPanel.tsx frontend/src/test/DesignKit.test.tsx
git commit -m "fix: resolve design kit hook lint errors"
```

---

## Verification Matrix

Run after each affected slice:

```powershell
cd frontend
npm.cmd run lint
npx.cmd tsc -b --noEmit
npm.cmd test
```

Run after backend slices:

```powershell
cd backend
python -m pytest tests/ -q -k "not PromptComposition"
```

Run before pushing:

```powershell
git status --short --branch
git log --oneline -5
```

---

## Self-Review

Spec coverage:
- v2 artifact pipeline: Tasks 3-5.
- Discovery gating and completion semantics: Task 2.
- DesignKit usability: Tasks 1, 2, 6.
- Sharing feedback/rating: Task 7.
- Auth/readiness: Task 8.
- Entitlements/security: Tasks 9-10.
- Billing: Task 11.
- Ops/docs/tests: Task 12.

Placeholder scan:
- No `TBD`, `TODO`, or “implement later” placeholders remain in the task steps.

Type consistency:
- `build_artifact_context(db, project_id, user_id)` is used consistently.
- Frontend helper is consistently named `hasMeaningfulValue`.
- `authFetch` always requires a token; `optionalAuthHeaders` handles public/private hybrid endpoints.
