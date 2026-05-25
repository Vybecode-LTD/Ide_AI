"""
modules.py — API endpoints for individual module execution.
Handles starting modules, processing responses (SSE streaming), and summaries.
"""
import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.design_sheet import DesignSheet
from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.project import Project
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.module_pathway import (
    ModuleRespondPayload,
    ModuleResponseRead,
    ModuleSummaryResponse,
)
from app.services.module_service import (
    _question_range,
    build_module_system_prompt,
    count_questions_asked,
    cross_populate_fields,
    extract_module_output,
    generate_first_question,
    is_existing_module,
    is_module_complete,
    stream_module_response,
)
from app.services.modular_pathway_service import get_module_definition

router = APIRouter(prefix="/modules", tags=["modules"])


async def _sync_pathway_completion(project_id: uuid.UUID, db: AsyncSession) -> str | None:
    """Update ModulePathway.status based on module response states.

    Sets ``"complete"`` when every module in the pathway is either complete
    or skipped.  Re-opens to ``"active"`` if a previously complete pathway
    has an incomplete module (e.g. after a module reset).

    Returns the new pathway status, or *None* if no pathway exists.
    """
    pw_result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = pw_result.scalar_one_or_none()
    if not pathway or not pathway.modules:
        return None

    responses_result = await db.execute(
        select(ModuleResponse).where(ModuleResponse.project_id == project_id)
    )
    status_map = {r.module_id: r.status for r in responses_result.scalars().all()}
    all_done = all(
        status_map.get(mid) in {"complete", "skipped"} for mid in pathway.modules
    )

    if all_done:
        pathway.status = "complete"
    elif pathway.status == "complete":
        pathway.status = "active"

    await db.flush()
    return pathway.status


async def _get_project_for_module(
    project_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Fetch project, verify ownership and pathway lock."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.pathway_locked:
        raise HTTPException(status_code=400, detail="Pathway must be locked before starting modules")
    return project


async def _get_concept_sheet_dict(project_id: uuid.UUID, db: AsyncSession) -> dict:
    """Load concept sheet as dict."""
    result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    sheet = result.scalar_one_or_none()
    if not sheet:
        return {}
    data = {
        "problem": sheet.problem,
        "audience": sheet.audience,
        "mvp": sheet.mvp,
        "tone": sheet.tone,
        "platform": sheet.platform,
        "tech_constraints": sheet.tech_constraints,
        "success_metric": sheet.success_metric,
        "features": sheet.features or [],
        "fields_data": sheet.fields_data or {},
        "confidence_score": sheet.confidence_score,
    }
    return {k: v for k, v in data.items() if v is not None}


async def _get_completed_module_outputs(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, dict]:
    """Load extracted outputs from all completed modules for cross-population."""
    result = await db.execute(
        select(ModuleResponse).where(
            ModuleResponse.project_id == project_id,
            ModuleResponse.status == "complete",
        )
    )
    completed = {}
    for mr in result.scalars().all():
        responses = mr.responses or {}
        extracted = responses.get("extracted", {})
        if extracted:
            completed[mr.module_id] = extracted
    return completed


# ── Start Module ─────────────────────────────────────────────────────

@router.post("/{project_id}/{module_id}/start")
async def start_module(
    project_id: uuid.UUID,
    module_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initialize a module session and return the first AI question."""
    project = await _get_project_for_module(project_id, current_user, db)

    # Verify module is in the pathway
    pathway_result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = pathway_result.scalar_one_or_none()
    if not pathway or module_id not in pathway.modules:
        raise HTTPException(status_code=400, detail="Module not in project pathway")

    # Check if this is an existing module (routes to dedicated page)
    if is_existing_module(module_id):
        return {
            "module_id": module_id,
            "existing_module": True,
            "redirect": f"/{module_id.replace('_', '-')}",
            "message": "This module has a dedicated page.",
        }

    defn = get_module_definition(module_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Module not found")

    # Get or create module response record
    mr_result = await db.execute(
        select(ModuleResponse).where(
            ModuleResponse.project_id == project_id,
            ModuleResponse.module_id == module_id,
        )
    )
    module_resp = mr_result.scalar_one_or_none()

    mode = pathway.lite_deep_settings.get(module_id, "lite")

    _min_q, max_q_start = _question_range(mode)

    # Resume: return existing active session messages instead of overwriting
    if module_resp and module_resp.status == "active":
        messages = (module_resp.responses or {}).get("messages", [])
        return {
            "module_id": module_id,
            "label": defn["label"],
            "messages": messages,
            "question_number": sum(1 for m in messages if m.get("role") == "assistant"),
            "total_questions": max_q_start,
            "mode": mode,
            "resumed": True,
        }

    # Completed: return transcript and extracted output for review
    if module_resp and module_resp.status == "complete":
        return {
            "module_id": module_id,
            "label": defn["label"],
            "already_complete": True,
            "messages": (module_resp.responses or {}).get("messages", []),
            "extracted": (module_resp.responses or {}).get("extracted", {}),
        }

    # Fresh start: generate first question
    completed_outputs = await _get_completed_module_outputs(project_id, db)
    pre_populated = cross_populate_fields(completed_outputs, module_id)

    concept_sheet = await _get_concept_sheet_dict(project_id, db)

    first_question = await generate_first_question(
        module_id,
        concept_sheet,
        ai_partner_style=project.ai_partner_style or "strategist",
        mode=mode,
        pre_populated=pre_populated,
    )

    # Create new module response record
    module_resp = ModuleResponse(
        project_id=project_id,
        module_id=module_id,
        responses={"messages": [{"role": "assistant", "content": first_question}]},
        status="active",
    )
    db.add(module_resp)

    await db.commit()

    return {
        "module_id": module_id,
        "label": defn["label"],
        "question": first_question,
        "question_number": 1,
        "total_questions": max_q_start,
        "mode": mode,
    }


# ── Respond to Module Question (SSE) ────────────────────────────────

@router.post("/{project_id}/{module_id}/respond")
async def respond_to_module(
    project_id: uuid.UUID,
    module_id: str,
    payload: ModuleRespondPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process user response and stream next AI question via SSE."""
    project = await _get_project_for_module(project_id, current_user, db)

    if is_existing_module(module_id):
        raise HTTPException(status_code=400, detail="Existing modules don't use this endpoint")

    # Load module response record
    mr_result = await db.execute(
        select(ModuleResponse).where(
            ModuleResponse.project_id == project_id,
            ModuleResponse.module_id == module_id,
        )
    )
    module_resp = mr_result.scalar_one_or_none()
    if not module_resp:
        raise HTTPException(status_code=404, detail="Module session not started")
    if module_resp.status == "complete":
        raise HTTPException(status_code=400, detail="Module already completed")

    # Load pathway for mode
    pw_result = await db.execute(
        select(ModulePathway).where(ModulePathway.project_id == project_id)
    )
    pathway = pw_result.scalar_one_or_none()
    mode = pathway.lite_deep_settings.get(module_id, "lite") if pathway else "lite"

    # Append user message
    messages = module_resp.responses.get("messages", [])
    messages.append({"role": "user", "content": payload.content})

    # Build Claude messages
    claude_messages = [{"role": m["role"], "content": m["content"]} for m in messages]

    # Count questions already asked (assistant messages before this response)
    questions_asked = count_questions_asked(messages)

    # Build system prompt with cross-populated context + question count
    concept_sheet = await _get_concept_sheet_dict(project_id, db)
    completed_outputs = await _get_completed_module_outputs(project_id, db)
    pre_populated = cross_populate_fields(completed_outputs, module_id)

    system_prompt = build_module_system_prompt(
        module_id,
        concept_sheet,
        ai_partner_style=project.ai_partner_style or "strategist",
        mode=mode,
        pre_populated=pre_populated,
        questions_asked=questions_asked,
    )

    _min_q, max_q = _question_range(mode)

    # Stream response
    async def event_stream():
        full_response = []
        async for token in stream_module_response(claude_messages, system_prompt):
            full_response.append(token)
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        response_text = "".join(full_response)
        complete = is_module_complete(response_text)

        # Force-complete if AI exceeded question limit without emitting marker
        new_question_count = questions_asked + 1  # this response is another assistant turn
        if not complete and new_question_count >= max_q:
            complete = True

        # Store assistant message
        messages.append({"role": "assistant", "content": response_text})

        # Update module response record
        module_resp.responses = {"messages": messages}
        if complete:
            module_resp.status = "complete"
            module_resp.completed_at = datetime.now(timezone.utc)
            # Extract structured output
            extracted = await extract_module_output(module_id, messages)
            current_data = module_resp.responses
            current_data["extracted"] = extracted
            module_resp.responses = current_data

        # Sync pathway completion status when a module finishes
        pathway_new_status = None
        if complete:
            pathway_new_status = await _sync_pathway_completion(project_id, db)

        await db.commit()

        # Parse chips from response
        chips = []
        chip_match = re.search(r"\[(?:CHIPS|chips|Chips):\s*(.*?)\]\s*[.!]?\s*$", response_text)
        if chip_match:
            chips = [c.strip() for c in chip_match.group(1).split("|") if c.strip()]

        question_number = sum(1 for m in messages if m.get("role") == "assistant")

        yield f"data: {json.dumps({'type': 'done', 'complete': complete, 'question_number': question_number, 'chips': chips, 'pathway_status': pathway_new_status})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ── Skip Module ──────────────────────────────────────────────────────

@router.post("/{project_id}/{module_id}/skip")
async def skip_module(
    project_id: uuid.UUID,
    module_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a module as skipped."""
    await _get_project_for_module(project_id, current_user, db)

    mr_result = await db.execute(
        select(ModuleResponse).where(
            ModuleResponse.project_id == project_id,
            ModuleResponse.module_id == module_id,
        )
    )
    module_resp = mr_result.scalar_one_or_none()

    if module_resp:
        module_resp.status = "skipped"
    else:
        module_resp = ModuleResponse(
            project_id=project_id,
            module_id=module_id,
            responses={"messages": [], "skipped": True},
            status="skipped",
        )
        db.add(module_resp)

    pathway_new_status = await _sync_pathway_completion(project_id, db)
    await db.commit()
    return {"module_id": module_id, "status": "skipped", "pathway_status": pathway_new_status}


# ── Module Summary ───────────────────────────────────────────────────

@router.get("/{project_id}/{module_id}/summary", response_model=ModuleSummaryResponse)
async def get_module_summary(
    project_id: uuid.UUID,
    module_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return structured summary of a completed module."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    mr_result = await db.execute(
        select(ModuleResponse).where(
            ModuleResponse.project_id == project_id,
            ModuleResponse.module_id == module_id,
        )
    )
    module_resp = mr_result.scalar_one_or_none()
    if not module_resp:
        raise HTTPException(status_code=404, detail="Module not started")

    defn = get_module_definition(module_id) or {"label": module_id}

    return {
        "module_id": module_id,
        "label": defn.get("label", module_id),
        "status": module_resp.status,
        "responses": module_resp.responses,
        "extracted": (module_resp.responses or {}).get("extracted", {}),
    }


# ── Module Responses List ────────────────────────────────────────────

@router.get("/{project_id}/responses", response_model=list[ModuleResponseRead])
async def list_module_responses(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all module responses for a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    mr_result = await db.execute(
        select(ModuleResponse).where(ModuleResponse.project_id == project_id)
    )
    return mr_result.scalars().all()


@router.patch("/{project_id}/{module_id}/responses", response_model=ModuleResponseRead)
async def update_module_responses(
    project_id: uuid.UUID,
    module_id: str,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partial-update field values on a module response.

    Validates keys against the module's field schema (rejects unknown keys)
    and coerces values to declared types (same defense as apply_extracted_module_fields).
    """
    from app.services.discovery_service import _coerce_field_value

    # Ownership check
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    # Load module definition for schema validation
    defn = get_module_definition(module_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Module not found in library")

    fields = defn.get("fields") or []
    valid_keys = {f["key"]: f.get("type", "text") for f in fields if f.get("key")}

    # Validate + coerce each incoming field
    coerced: dict = {}
    rejected: list[str] = []
    for key, value in payload.items():
        if key not in valid_keys:
            rejected.append(key)
            continue
        result = _coerce_field_value(value, valid_keys[key])
        if result is not None:
            coerced[key] = result

    if rejected:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown field keys: {', '.join(rejected)}",
        )

    if not coerced:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # Upsert: find existing response or create new one
    mr_result = await db.execute(
        select(ModuleResponse).where(
            ModuleResponse.project_id == project_id,
            ModuleResponse.module_id == module_id,
        )
    )
    mr = mr_result.scalar_one_or_none()

    if mr:
        mr.responses = {**(mr.responses or {}), **coerced}
    else:
        mr = ModuleResponse(
            project_id=project_id,
            module_id=module_id,
            responses=coerced,
            status="active",
        )
        db.add(mr)

    await db.commit()
    await db.refresh(mr)
    return mr


@router.post("/{project_id}/{module_id}/refresh-output")
async def refresh_module_output(
    project_id: uuid.UUID,
    module_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate or regenerate rich output for a has_output module.

    Uses the module's current field values to produce a formatted document.
    Returns 400 if the module doesn't have has_output: true.
    """
    from app.services.module_service import generate_module_output

    # Ownership check
    proj_result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    defn = get_module_definition(module_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Module not found in library")

    if not defn.get("has_output"):
        raise HTTPException(status_code=400, detail="Module does not support output generation")

    # Get current field values
    mr_result = await db.execute(
        select(ModuleResponse).where(
            ModuleResponse.project_id == project_id,
            ModuleResponse.module_id == module_id,
        )
    )
    mr = mr_result.scalar_one_or_none()
    field_values = (mr.responses or {}) if mr else {}

    output = await generate_module_output(
        module_id=module_id,
        field_values=field_values,
        project_name=project.name,
    )

    # Store the generated output alongside field values
    if mr:
        mr.responses = {**(mr.responses or {}), "__generated_output": output}
    else:
        mr = ModuleResponse(
            project_id=project_id,
            module_id=module_id,
            responses={"__generated_output": output},
            status="active",
        )
        db.add(mr)

    await db.commit()
    await db.refresh(mr)
    return output
