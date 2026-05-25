"""
discovery.py — Discovery session router. Handles SSE streaming AI conversations.
"""
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.module_pathway import ModulePathway
from app.models.project import Project
from app.models.user import User
from app.pathways import PathwayRegistry
from app.routers.auth import get_current_user
from app.schemas.session import MessagePayload, PartnerUpdatePayload, ProgressPayload, SessionCreate, SessionRead
from app.schemas.design_sheet import DesignSheetRead
from app.services import discovery_service, ai_service, modular_pathway_service, transcript_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.post("/start", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new discovery session for a project."""
    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == payload.project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate scope_module_ids against the project's actual pathway
    if payload.scope_module_ids:
        if getattr(project, "flow_version", "v1") != "v2":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scoped sessions are only supported for v2 projects",
            )
        pw_result = await db.execute(
            select(ModulePathway).where(ModulePathway.project_id == payload.project_id)
        )
        pathway = pw_result.scalar_one_or_none()
        if not pathway or not pathway.modules:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no module pathway",
            )
        valid_ids = {m if isinstance(m, str) else m.get("id", "") for m in pathway.modules}
        invalid = set(payload.scope_module_ids) - valid_ids
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid module IDs in scope: {', '.join(sorted(invalid))}",
            )

    try:
        session, created = await discovery_service.create_or_resume_session(
            db,
            payload.project_id,
            force_new=payload.force_new,
            scope_module_ids=payload.scope_module_ids,
        )

        # Only set partner style for new sessions or legacy sessions missing it
        if created or not getattr(session, "ai_partner_style", None):
            session.ai_partner_style = getattr(project, "ai_partner_style", "strategist")

        await db.commit()
        await db.refresh(session)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return session


@router.post("/{session_id}/init")
async def init_greeting(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate the AI's opening greeting for a discovery session. No user message needed."""
    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if session.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session is not active")

    # Don't re-init if session already has messages
    if session.messages and len(session.messages) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session already initialized")

    # Resolve the project's pathway
    pw = PathwayRegistry.get_or_default(project.pathway_id)

    # Branch on flow_version: v2 projects get a unified-aware greeting that
    # references the assembled module set; v1 keeps the legacy stage-based
    # greeting. Closes audit finding M3. Falls back to the legacy greeting
    # if the v2 pathway happens to be empty (defensive — should not happen
    # post-H1 fix in projects.py which downgrades empty v2 projects to v1).
    if getattr(project, "flow_version", "v1") == "v2":
        decorated = await discovery_service.load_decorated_pathway_modules(db, project.id)
        if decorated and session.scope_module_ids:
            scope_set = set(session.scope_module_ids)
            decorated = [m for m in decorated if m["module_id"] in scope_set]
        if decorated:
            system_prompt = await ai_service.build_unified_greeting_prompt(
                project_name=project.name,
                project_description=project.description,
                primary_category=project.primary_category,
                platform=project.platform or "custom",
                modules=decorated,
                ai_partner_style=session.ai_partner_style,
            )
        else:
            system_prompt = await ai_service.build_greeting_prompt(
                project_description=project.description,
                platform=project.platform or "custom",
                pathway=pw,
                ai_partner_style=session.ai_partner_style,
            )
    else:
        system_prompt = await ai_service.build_greeting_prompt(
            project_description=project.description,
            platform=project.platform or "custom",
            pathway=pw,
            ai_partner_style=session.ai_partner_style,
        )

    # The AI speaks first — no user message in the history
    claude_messages = [{"role": "user", "content": f"I want to build: {project.description or project.name}"}]

    _CHIP_FALLBACK = ["Yes, exactly", "Not quite — let me explain", "I have a different angle"]

    async def event_stream():
        full_response = []

        async for token in ai_service.stream_response(claude_messages, system_prompt):
            full_response.append(token)
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        ai_text = "".join(full_response)

        # Save message — non-fatal if it fails, rollback so subsequent code
        # doesn't run against an aborted session
        try:
            clean_text = ai_service.strip_chips_line(ai_text)
            await discovery_service.add_message(db, session, "assistant", clean_text)
            await db.commit()
        except Exception as exc:
            logger.warning("Failed to save greeting message: %s", exc)
            try:
                await db.rollback()
            except Exception:
                pass

        # ALWAYS send completion event with chips — wrapped so any parse or
        # serialization issue still yields a usable done sentinel
        try:
            chips = await ai_service.generate_quick_chips(
                ai_text, stage=session.stage or "greeting"
            )
            if not chips:
                chips = _CHIP_FALLBACK
        except Exception as exc:
            logger.error("generate_quick_chips raised (init): %s", exc)
            chips = _CHIP_FALLBACK

        try:
            yield f"data: {json.dumps({'type': 'done', 'stage': session.stage, 'chips': chips})}\n\n"
        except Exception as exc:
            logger.error("Failed to emit done event (init): %s", exc)
            yield 'data: {"type": "done", "stage": "", "chips": ["Yes, exactly", "Not quite", "I have a different angle"]}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{session_id}/message")
async def send_message(
    session_id: uuid.UUID,
    payload: MessagePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a discovery session. Returns SSE stream."""
    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if session.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session is not active")

    # Add user message
    await discovery_service.add_message(db, session, "user", payload.content)
    await db.commit()

    # Resolve project (used by both v1 and v2 branches)
    proj_result = await db.execute(select(Project).where(Project.id == session.project_id))
    project = proj_result.scalar_one_or_none()
    platform = project.platform if project else "custom"
    pw = PathwayRegistry.get_or_default(project.pathway_id if project else None)

    # ── Flow-version branch ──
    # v2 projects use a unified-discovery prompt that targets all module
    # field schemas at once and writes into module_responses. v1 projects
    # keep the original stage-based prompt + design_sheet behavior intact.
    use_v2_flow = False
    pathway_modules: list[dict] = []
    current_fields: dict[str, dict] = {}

    if project and getattr(project, "flow_version", "v1") == "v2":
        mp_result = await db.execute(
            select(ModulePathway).where(ModulePathway.project_id == project.id)
        )
        mp = mp_result.scalar_one_or_none()
        if mp and mp.modules:
            # mp.modules stores module-id strings (per PathwayRead schema).
            # Decorate each ID into a full module entry with label + fields +
            # has_output by looking up the library definition. Skips unknown
            # IDs gracefully. Tolerates legacy list[dict] shape too in case
            # migration 030 hasn't run yet for a given DB.
            raw_entries = list(mp.modules)
            decorated: list[dict] = []
            for raw in raw_entries:
                mid = raw if isinstance(raw, str) else (raw.get("module_id") if isinstance(raw, dict) else None)
                if not mid:
                    continue
                defn = modular_pathway_service.get_module_definition(mid)
                if not defn:
                    continue
                decorated.append({
                    "module_id": mid,
                    "label": defn.get("label", mid),
                    "description": defn.get("description", ""),
                    "group": defn.get("group", ""),
                    "fields": list(defn.get("fields") or []),
                    "has_output": bool(defn.get("has_output")),
                })

            if decorated and session.scope_module_ids:
                scope_set = set(session.scope_module_ids)
                decorated = [m for m in decorated if m["module_id"] in scope_set]
            if decorated:
                use_v2_flow = True
                pathway_modules = decorated
                current_fields = await discovery_service.get_filled_fields_for_project(
                    db, project.id
                )

    if use_v2_flow:
        system_prompt = await ai_service.build_unified_discovery_prompt(
            project_name=project.name,
            project_description=project.description,
            primary_category=project.primary_category,
            platform=project.platform,
            modules=pathway_modules,
            current_fields=current_fields,
            ai_partner_style=session.ai_partner_style,
            message_count=len(session.messages or []),
        )
    else:
        # Legacy v1 path — design-sheet-driven prompt
        sheet = await discovery_service.get_sheet_for_project(db, session.project_id)
        sheet_context = None
        if sheet:
            sheet_context = {
                "problem": sheet.problem,
                "audience": sheet.audience,
                "mvp": sheet.mvp,
                "platform": sheet.platform,
                "tone": sheet.tone,
            }
        system_prompt = await ai_service.build_system_prompt(
            platform, session.stage, sheet_context,
            pathway=pw, ai_partner_style=session.ai_partner_style,
            message_count=len(session.messages or []),
        )

    # Build Claude message history
    claude_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in (session.messages or [])
    ]

    # Generic 3-item fallback used when chip generation itself fails so the
    # UI never ends up with an empty chip list.
    _CHIP_FALLBACK = ["Yes, exactly", "Not quite — let me explain", "I have a different angle"]

    async def event_stream():
        full_response = []

        async for token in ai_service.stream_response(claude_messages, system_prompt):
            full_response.append(token)
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

        # Assemble full response
        ai_text = "".join(full_response)
        clean_text = ai_service.strip_chips_line(ai_text)

        # Step 1: Persist the assistant message in its OWN transaction so it
        # survives even if the sheet extraction or follow-up commits explode.
        # Resume relies on this — if we don't commit here, the AI side is lost.
        try:
            await discovery_service.add_message(db, session, "assistant", clean_text)
            await db.commit()
        except Exception as exc:
            logger.error("Failed to persist assistant message: %s", exc)
            try:
                await db.rollback()
            except Exception:
                pass

        # Step 2: Extract — branch on flow_version.
        # v2: extract per-module field values, write to module_responses,
        #     emit a `field_update` SSE event with the per-module summary.
        # v1: extract design-sheet fields, emit the existing `sheet_update`.
        sheet_data: dict | None = None
        v2_payload: dict | None = None

        if use_v2_flow:
            try:
                # Use the freshly-updated session.messages (now includes the assistant turn)
                latest_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in (session.messages or [])
                ]
                extracted = await ai_service.extract_module_fields(
                    latest_messages, pathway_modules, current_fields
                )
                updates_list, summary = await discovery_service.apply_extracted_module_fields(
                    db, project.id, extracted, pathway_modules
                )
                await db.commit()
                v2_payload = {"updates": updates_list, "summary": summary}
            except Exception as exc:
                logger.warning("Module field extraction/commit failed: %s", exc)
                try:
                    await db.rollback()
                except Exception:
                    pass
                v2_payload = None
        else:
            try:
                updated_sheet, sheet_changed = await discovery_service.update_sheet_from_conversation(
                    db, session, pathway=pw
                )
                if sheet_changed and updated_sheet:
                    sheet_data = {
                        "problem": updated_sheet.problem,
                        "audience": updated_sheet.audience,
                        "mvp": updated_sheet.mvp,
                        "features": updated_sheet.features,
                        "tone": updated_sheet.tone,
                        "platform": updated_sheet.platform,
                        "tech_constraints": updated_sheet.tech_constraints,
                        "success_metric": updated_sheet.success_metric,
                        "confidence_score": updated_sheet.confidence_score,
                    }
                    await db.commit()
            except Exception as exc:
                logger.warning("Sheet extraction/commit failed: %s", exc)
                try:
                    await db.rollback()
                except Exception:
                    pass
                sheet_data = None

        # Step 3: Emit extraction-derived event BEFORE done so clients that
        # close the stream on the done sentinel still receive the payload.
        # ``default=str`` defends against any stray non-JSON-native types that
        # might sneak in via JSONB columns (datetimes, Decimals, UUIDs, etc.).
        if v2_payload is not None:
            try:
                yield f"data: {json.dumps({'type': 'field_update', **v2_payload}, default=str)}\n\n"
            except Exception as exc:
                logger.error("Failed to emit field_update event: %s", exc)
        elif sheet_data is not None:
            try:
                yield f"data: {json.dumps({'type': 'sheet_update', 'sheet': sheet_data}, default=str)}\n\n"
            except Exception as exc:
                logger.error("Failed to emit sheet_update event: %s", exc)

        # Step 4: ALWAYS emit a done event. Two layers of fallback:
        #   - generate_quick_chips wrapped so a parse error doesn't kill the stream
        #   - the final yield is itself wrapped so a serialization issue still
        #     produces a minimal done sentinel for the client
        try:
            chips = await ai_service.generate_quick_chips(
                ai_text, stage=session.stage or "greeting"
            )
            if not chips:
                chips = _CHIP_FALLBACK
        except Exception as exc:
            logger.error("generate_quick_chips raised: %s", exc)
            chips = _CHIP_FALLBACK

        try:
            yield f"data: {json.dumps({'type': 'done', 'stage': session.stage, 'chips': chips})}\n\n"
        except Exception as exc:
            logger.error("Failed to emit done event: %s", exc)
            # Last-ditch fallback — minimal done sentinel so the client unsticks
            yield 'data: {"type": "done", "stage": "", "chips": ["Yes, exactly", "Not quite", "I have a different angle"]}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{session_id}/field-summary")
async def get_field_summary(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current field-completion summary for a v2 discovery session.

    Used by the frontend ProgressPanel to hydrate on mount / resume — without
    this endpoint the panel sits empty until the user's next message triggers
    a ``field_update`` SSE event. Closes audit finding M6.

    Returns ``404`` if the session doesn't exist or the user doesn't own its
    project. Returns ``409`` if the project is v1 (no module pathway to
    summarize) so the client knows to render the legacy DesignSheetPanel
    instead.
    """
    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if getattr(project, "flow_version", "v1") != "v2":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is on the v1 discovery flow; no field summary available",
        )

    decorated = await discovery_service.load_decorated_pathway_modules(db, project.id)
    if session.scope_module_ids:
        scope_set = set(session.scope_module_ids)
        decorated = [m for m in decorated if m["module_id"] in scope_set]
    summary = await discovery_service.compute_field_summary(db, project.id, decorated)
    return summary


@router.patch("/{session_id}/progress")
async def save_progress(
    session_id: uuid.UUID,
    payload: ProgressPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save current discovery progress without side effects.

    Used for auto-save (every 30s, on stage change, visibility-hidden, and
    unmount).  The client sends only ``stage`` and ``client_message_count``.
    The backend never accepts a raw messages array from the browser — it is
    the canonical owner of persisted messages.

    If the client's message count is lower than the server's, the save is
    treated as stale and silently ignored (no data overwritten).
    """
    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    server_count = len(session.messages or [])

    # Guard: if the client is behind the server, do not mutate anything.
    if payload.client_message_count is not None and payload.client_message_count < server_count:
        return {
            "status": "ignored_stale_client",
            "session_id": str(session_id),
            "server_message_count": server_count,
        }

    # Only update stage — messages are never overwritten by the client.
    if payload.stage:
        session.stage = payload.stage
    await db.commit()

    return {"status": "saved", "session_id": str(session_id)}


@router.get("/{session_id}/transcript")
async def export_transcript(
    session_id: uuid.UUID,
    format: str = Query("txt", pattern="^(txt|pdf|md)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export the discovery conversation transcript as TXT, PDF, or Markdown."""
    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    messages = session.messages or []
    project_name = project.name

    if format == "pdf":
        content = transcript_service.format_as_pdf(messages, project_name)
        slug = project_name.lower().replace(" ", "-")[:30]
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{slug}-transcript.pdf"'},
        )
    elif format == "md":
        content = transcript_service.format_as_markdown(messages, project_name)
        slug = project_name.lower().replace(" ", "-")[:30]
        return Response(
            content=content.encode("utf-8"),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{slug}-transcript.md"'},
        )
    else:
        content = transcript_service.format_as_text(messages, project_name)
        slug = project_name.lower().replace(" ", "-")[:30]
        return Response(
            content=content.encode("utf-8"),
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{slug}-transcript.txt"'},
        )


@router.patch("/{session_id}/partner")
async def update_partner(
    session_id: uuid.UUID,
    payload: PartnerUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch AI partner mid-session. Persists to both session and project."""
    from app.services.partner_style_service import validate_partner_style

    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        style = validate_partner_style(payload.ai_partner_style)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    session.ai_partner_style = style
    project.ai_partner_style = style
    await db.commit()

    return {"status": "updated", "ai_partner_style": style}


@router.get("/{session_id}", response_model=SessionRead)
async def get_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a discovery session by ID."""
    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return session


@router.get("/{session_id}/sheet", response_model=DesignSheetRead)
async def get_sheet(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current design sheet state for a session."""
    session = await discovery_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Verify project ownership
    proj_result = await db.execute(
        select(Project).where(Project.id == session.project_id, Project.user_id == current_user.id)
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    sheet = await discovery_service.get_sheet_for_project(db, session.project_id)
    if not sheet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Design sheet not found")
    return sheet
