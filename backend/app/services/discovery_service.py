"""
discovery_service.py — Socratic discovery engine with state machine and confidence scoring.
Manages the discovery flow and auto-updates the design sheet.
Stage order, transitions, and confidence weights are driven by the active PathwayConfig.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import case, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import DiscoverySession
from app.models.design_sheet import DesignSheet
from app.models.project import Project
from app.services.ai_service import extract_sheet_fields

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.pathways.base import PathwayConfig


def _get_pathway(pathway: PathwayConfig | None = None) -> PathwayConfig:
    """Resolve a pathway, falling back to software_product."""
    if pathway is not None:
        return pathway
    from app.pathways import PathwayRegistry
    return PathwayRegistry.get("software_product")


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

async def get_latest_active_session_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> DiscoverySession | None:
    """Return the best active discovery session for a project.

    Prefers a non-empty session (one with at least one message) over a newer
    empty one.  This recovers users who hit the old empty-session bug: the
    latest session may be an empty orphan while the real conversation sits in
    an older row.
    """
    message_count = func.coalesce(func.jsonb_array_length(DiscoverySession.messages), 0)

    result = await db.execute(
        select(DiscoverySession)
        .where(
            DiscoverySession.project_id == project_id,
            DiscoverySession.status == "active",
        )
        .order_by(
            # Non-empty sessions sort first (0 < 1)
            case((message_count > 0, 0), else_=1),
            DiscoverySession.updated_at.desc(),
            DiscoverySession.created_at.desc(),
        )
        .limit(1)
    )
    selected = result.scalar_one_or_none()

    if selected is not None:
        # Retire newer empty orphan sessions so they don't reappear.
        empty_sessions = await db.execute(
            select(DiscoverySession).where(
                DiscoverySession.project_id == project_id,
                DiscoverySession.status == "active",
                DiscoverySession.id != selected.id,
                func.coalesce(func.jsonb_array_length(DiscoverySession.messages), 0) == 0,
            )
        )
        for orphan in empty_sessions.scalars():
            orphan.status = "abandoned"

    return selected


async def create_or_resume_session(
    db: AsyncSession,
    project_id: uuid.UUID,
    *,
    force_new: bool = False,
) -> tuple[DiscoverySession, bool]:
    """Return an active session for the project, creating one only if needed.

    Returns:
        (session, created) — created is True when a new session was made.
    """
    if not force_new:
        existing = await get_latest_active_session_for_project(db, project_id)
        if existing:
            return existing, False

    session = await create_session(db, project_id)
    return session, True


async def create_session(db: AsyncSession, project_id: uuid.UUID) -> DiscoverySession:
    """Create a new discovery session and initialize an empty design sheet."""
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Create session
    session = DiscoverySession(
        project_id=project_id,
        status="active",
        stage="greeting",
        messages=[],
    )
    db.add(session)

    # Create design sheet if it doesn't exist
    existing_sheet = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    if not existing_sheet.scalar_one_or_none():
        sheet = DesignSheet(
            project_id=project_id,
            platform=project.platform,
            tone=project.tone,
        )
        db.add(sheet)

    await db.flush()
    return session


async def add_message(
    db: AsyncSession, session: DiscoverySession, role: str, content: str
) -> DiscoverySession:
    """Append a message to the session's message history."""
    messages = list(session.messages or [])
    messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    session.messages = messages
    await db.flush()
    return session


# ---------------------------------------------------------------------------
# Stage machine — driven by PathwayConfig.stages
# ---------------------------------------------------------------------------

def _get_sheet_value(sheet: DesignSheet, field_key: str) -> object:
    """Get a design sheet field value, checking named columns first, then fields_data."""
    # Named columns (used by the software pathway)
    val = getattr(sheet, field_key, None)
    if val:
        return val
    # Generic JSONB storage (used by other pathways)
    if sheet.fields_data and field_key in sheet.fields_data:
        return sheet.fields_data[field_key]
    return None


def next_stage(
    current_stage: str,
    sheet: DesignSheet,
    pathway: PathwayConfig | None = None,
) -> str:
    """Determine the next discovery stage based on current state and sheet completeness.

    Uses the pathway's stage list to determine ordering and checks
    each stage's ``required_fields`` for advancement.
    """
    pw = _get_pathway(pathway)
    stage_ids = [s.id for s in pw.stages]

    # If current stage isn't in the pathway (shouldn't happen), stay put
    if current_stage not in stage_ids:
        return current_stage

    current_idx = stage_ids.index(current_stage)

    # Already at the last stage — stay
    if current_idx >= len(stage_ids) - 1:
        return current_stage

    # Greeting always advances immediately
    if current_stage == "greeting":
        return stage_ids[current_idx + 1]

    # For other stages, check required_fields of the CURRENT stage
    current_stage_cfg = pw.stages[current_idx]
    if current_stage_cfg.required_fields:
        all_filled = all(
            _get_sheet_value(sheet, f) for f in current_stage_cfg.required_fields
        )
        if all_filled:
            return stage_ids[current_idx + 1]
        # Stay on current stage if key fields aren't filled yet
        return current_stage

    # No required fields — advance
    return stage_ids[current_idx + 1]


# ---------------------------------------------------------------------------
# Confidence scoring — driven by PathwayConfig.sheet_fields
# ---------------------------------------------------------------------------

def compute_confidence(
    sheet: DesignSheet,
    pathway: PathwayConfig | None = None,
) -> int:
    """Compute confidence score (0-100) based on populated design sheet fields.

    Uses the pathway's ``sheet_fields`` weights.
    """
    pw = _get_pathway(pathway)
    score = 0
    for sf in pw.sheet_fields:
        value = _get_sheet_value(sheet, sf.key)
        if value:
            if isinstance(value, list) and len(value) > 0:
                score += sf.weight
            elif isinstance(value, str) and len(value.strip()) > 0:
                score += sf.weight
            elif isinstance(value, dict):
                score += sf.weight
    return min(score, 100)


# ---------------------------------------------------------------------------
# Sheet extraction & update
# ---------------------------------------------------------------------------

# Named columns on DesignSheet (software pathway backward compat)
_NAMED_COLUMNS = frozenset(
    ["problem", "audience", "mvp", "tone", "platform", "tech_constraints", "success_metric"]
)


async def update_sheet_from_conversation(
    db: AsyncSession,
    session: DiscoverySession,
    pathway: PathwayConfig | None = None,
) -> tuple[DesignSheet, bool]:
    """Extract fields from conversation and update the design sheet.
    Returns (updated_sheet, changed) tuple."""
    pw = _get_pathway(pathway)

    result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == session.project_id)
    )
    sheet = result.scalar_one_or_none()
    if not sheet:
        logger.warning("No design sheet found for project %s — creating one", session.project_id)
        # Auto-create a design sheet if missing (safety net)
        from app.models.project import Project as _Proj
        proj_r = await db.execute(select(_Proj).where(_Proj.id == session.project_id))
        project = proj_r.scalar_one_or_none()
        sheet = DesignSheet(
            project_id=session.project_id,
            platform=project.platform if project else None,
            tone=project.tone if project else None,
        )
        db.add(sheet)
        await db.flush()

    # Build Claude-compatible messages for extraction
    claude_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (session.messages or [])
    ]

    if not claude_messages:
        logger.debug("No messages in session — skipping extraction")
        return sheet, False

    logger.info("Extracting sheet fields from %d messages", len(claude_messages))
    extracted = await extract_sheet_fields(claude_messages, pathway=pw)
    if not extracted:
        logger.info("Extraction returned no fields (conversation may be too early)")
        return sheet, False

    changed = False

    # Determine which fields to update from the pathway's sheet_fields
    for sf in pw.sheet_fields:
        key = sf.key
        if key not in extracted or not extracted[key]:
            continue
        new_val = extracted[key]

        # Use named column if it exists on the model (software pathway compat)
        if key in _NAMED_COLUMNS:
            current = getattr(sheet, key, None)
            if new_val and new_val != current:
                setattr(sheet, key, new_val)
                changed = True
        else:
            # Store in generic fields_data JSONB
            fd = dict(sheet.fields_data or {})
            if fd.get(key) != new_val:
                fd[key] = new_val
                sheet.fields_data = fd
                changed = True

    # Handle features separately (list type, stored as named column for software)
    if "features" in extracted and isinstance(extracted["features"], list) and extracted["features"]:
        sheet.features = extracted["features"]
        changed = True

    if changed:
        sheet.confidence_score = compute_confidence(sheet, pw)
        # Check for stage advancement
        new_stage = next_stage(session.stage, sheet, pw)
        if new_stage != session.stage:
            session.stage = new_stage

    await db.flush()
    return sheet, changed


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------

async def get_session(db: AsyncSession, session_id: uuid.UUID) -> DiscoverySession | None:
    """Fetch a discovery session by ID."""
    result = await db.execute(
        select(DiscoverySession).where(DiscoverySession.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_sheet_for_project(db: AsyncSession, project_id: uuid.UUID) -> DesignSheet | None:
    """Fetch the design sheet for a project."""
    result = await db.execute(
        select(DesignSheet).where(DesignSheet.project_id == project_id)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Unified-discovery (v2) helpers — populate module_responses from conversation
# ---------------------------------------------------------------------------


async def get_filled_fields_for_project(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, dict]:
    """Return current state of module field values for a project.

    Returns a dict mapping ``module_id`` to ``{field_key: value}``. Used by
    the unified-discovery prompt builder to show the AI what's already filled.
    """
    from app.models.module_response import ModuleResponse
    result = await db.execute(
        select(ModuleResponse).where(ModuleResponse.project_id == project_id)
    )
    return {r.module_id: dict(r.responses or {}) for r in result.scalars().all()}


async def compute_field_summary(
    db: AsyncSession,
    project_id: uuid.UUID,
    modules: list[dict],
) -> dict:
    """Aggregate field-completion stats across all assembled modules.

    Returns the payload used by the SSE ``field_update`` event and the
    frontend progress meter:
      {
        "total_filled": int, "total_fields": int,
        "required_filled": int, "required_total": int,
        "overall_percent": int,
        "per_module": [
          {"module_id", "label", "filled", "total",
           "required_filled", "required_total"}
        ]
      }
    """
    from app.models.module_response import ModuleResponse
    result = await db.execute(
        select(ModuleResponse).where(ModuleResponse.project_id == project_id)
    )
    by_mid = {r.module_id: r for r in result.scalars().all()}

    per_module: list[dict] = []
    total_filled = 0
    total_fields = 0
    required_filled = 0
    required_total = 0

    for mod in modules:
        mid = mod.get("module_id") or mod.get("id")
        if not mid:
            continue
        fields = mod.get("fields") or []
        resp = by_mid.get(mid)
        filled_keys = set((resp.responses if resp else {}).keys())

        m_total = len(fields)
        m_filled = sum(1 for f in fields if f.get("key") in filled_keys)
        m_req_total = sum(1 for f in fields if f.get("required"))
        m_req_filled = sum(
            1 for f in fields if f.get("required") and f.get("key") in filled_keys
        )

        per_module.append({
            "module_id": mid,
            "label": mod.get("label", mid),
            "filled": m_filled,
            "total": m_total,
            "required_filled": m_req_filled,
            "required_total": m_req_total,
        })

        total_filled += m_filled
        total_fields += m_total
        required_filled += m_req_filled
        required_total += m_req_total

    return {
        "total_filled": total_filled,
        "total_fields": total_fields,
        "required_filled": required_filled,
        "required_total": required_total,
        "overall_percent": int((total_filled / total_fields * 100)) if total_fields else 0,
        "per_module": per_module,
    }


def _coerce_field_value(value, field_type: str):
    """Coerce an extracted value to the declared field schema type.

    Returns the coerced value, or ``None`` to indicate the value should be
    dropped (uncoerceable, empty, or wrong-shape for the declared type).
    Defends against the AI returning a string where a list was expected,
    a dict where a string was expected, etc.
    """
    import json as _json

    if value is None:
        return None

    if field_type in ("text", "longtext"):
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        if isinstance(value, (list, dict)):
            if not value:
                return None
            return _json.dumps(value)
        return str(value).strip() or None

    if field_type == "list":
        if isinstance(value, list):
            cleaned = [str(v).strip() for v in value if v not in (None, "", [], {})]
            return cleaned or None
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else None
        if isinstance(value, dict):
            vals = [str(v).strip() for v in value.values() if v]
            return vals or None
        return [str(value)] if value else None

    if field_type == "dict":
        if isinstance(value, dict):
            return value or None
        # Don't accept scalars for dict-typed fields — wrong shape.
        return None

    # Unknown field type — pass through unchanged.
    return value


async def apply_extracted_module_fields(
    db: AsyncSession,
    project_id: uuid.UUID,
    extracted: dict,
    modules: list[dict],
) -> tuple[list[dict], dict]:
    """Write extracted "module_id.field_key" updates into module_responses.

    Uses PostgreSQL ``INSERT ... ON CONFLICT (project_id, module_id) DO UPDATE``
    so concurrent calls from the same project (multi-tab, retry, etc.) don't
    create duplicate rows or lose updates. The unique constraint required by
    this is added in migration 030.

    Args:
        extracted: dict mapping "module_id.field_key" -> value (from
            :func:`ai_service.extract_module_fields`).
        modules: assembled module list (with embedded ``fields`` schemas) —
            used for type coercion + summary computation + valid-key filter.

    Returns:
        ``(updates_list, summary)`` where:
        - ``updates_list``: per-field update payload for the SSE
          ``field_update`` event (list of {module_id, field_key, value})
        - ``summary``: aggregate completion stats from
          :func:`compute_field_summary`
    """
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.models.module_response import ModuleResponse

    # Build (module_id, field_key) -> field_type lookup for coercion + key validation
    field_types: dict[tuple[str, str], str] = {}
    valid_module_ids: set[str] = set()
    for mod in modules:
        mid = mod.get("module_id") or mod.get("id")
        if not mid:
            continue
        valid_module_ids.add(mid)
        for f in mod.get("fields") or []:
            fkey = f.get("key")
            if fkey:
                field_types[(mid, fkey)] = f.get("type", "text")

    # Group extracted keys by module_id, applying type coercion
    by_module: dict[str, dict] = {}
    for compound_key, value in extracted.items():
        if "." not in compound_key:
            continue
        mid, fkey = compound_key.split(".", 1)
        if mid not in valid_module_ids or not fkey:
            continue
        ftype = field_types.get((mid, fkey), "text")
        coerced = _coerce_field_value(value, ftype)
        if coerced is None:
            continue
        by_module.setdefault(mid, {})[fkey] = coerced

    updates_list: list[dict] = []

    if by_module:
        # Race-safe upsert per module. The JSONB ``||`` operator merges the
        # incoming field_updates into the existing ``responses`` dict — keys
        # in EXCLUDED win, untouched keys are preserved.
        for mid, field_updates in by_module.items():
            stmt = pg_insert(ModuleResponse).values(
                project_id=project_id,
                module_id=mid,
                responses=field_updates,
                status="active",
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["project_id", "module_id"],
                set_={
                    "responses": text("module_responses.responses || EXCLUDED.responses"),
                    "status": text("'active'"),
                },
            )
            await db.execute(stmt)
            for fk, v in field_updates.items():
                updates_list.append({"module_id": mid, "field_key": fk, "value": v})

        await db.flush()

    summary = await compute_field_summary(db, project_id, modules)
    return updates_list, summary
