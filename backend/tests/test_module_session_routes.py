"""
test_module_session_routes.py — starting and answering an AI module session.

Regression tests for two faults in ``app/routers/modules.py``:

1. ``POST /modules/{project}/{module}/start`` read an undefined ``pathway``
   variable, so every start (and every resume) ended in a 500.
2. The session wrote ``responses = {"messages": ...}`` over the whole JSON
   column, which also holds the field values written by v2 discovery and the
   generated output. Answering one question erased them.

Only the AI boundary is mocked; routing, auth override, persistence and the
SSE stream run for real, through the production-style ``request_client``.
"""
import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.module_pathway import ModulePathway
from app.models.module_response import ModuleResponse
from app.models.project import Project
from tests.conftest import TestSessionLocal

MODULE = "audience_persona_builder"  # an AI-conversation module, not a page
FIRST_QUESTION = "Who is this for? [CHIPS: Founders | Students]"


@pytest.fixture
def ai(monkeypatch):
    """Replace the three Claude calls the module routes make."""

    async def first_question(module_id, concept_sheet, **kwargs):
        return FIRST_QUESTION

    async def stream(messages, system_prompt):
        for token in ("Got it. ", "What do they struggle with?"):
            yield token

    async def extract(module_id, messages):
        return {"summary": "extracted"}

    monkeypatch.setattr("app.routers.modules.generate_first_question", first_question)
    monkeypatch.setattr("app.routers.modules.stream_module_response", stream)
    monkeypatch.setattr("app.routers.modules.extract_module_output", extract)


async def _project_with_pathway(db: AsyncSession, user_id: uuid.UUID) -> uuid.UUID:
    pid = uuid.uuid4()
    db.add(Project(id=pid, user_id=user_id, name="P", description="d", pathway_locked=True))
    await db.flush()
    db.add(
        ModulePathway(
            project_id=pid,
            modules=[MODULE],
            lite_deep_settings={MODULE: "lite"},
            status="active",
        )
    )
    await db.flush()
    return pid


async def _rows(pid: uuid.UUID) -> list[ModuleResponse]:
    async with TestSessionLocal() as fresh:
        result = await fresh.execute(
            select(ModuleResponse).where(
                ModuleResponse.project_id == pid, ModuleResponse.module_id == MODULE
            )
        )
        return list(result.scalars().all())


def _sse_events(body: str) -> list[dict]:
    return [json.loads(line[6:]) for line in body.splitlines() if line.startswith("data: ")]


class TestStartModule:
    @pytest.mark.asyncio
    async def test_fresh_start_returns_the_first_question(
        self, db_session, test_user, request_client, ai
    ):
        pid = await _project_with_pathway(db_session, test_user.id)
        await db_session.commit()

        res = request_client.post(f"/api/v1/modules/{pid}/{MODULE}/start")

        assert res.status_code == 200, res.text
        body = res.json()
        assert body["question"] == FIRST_QUESTION
        assert body["mode"] == "lite"
        assert body["question_number"] == 1
        rows = await _rows(pid)
        assert len(rows) == 1
        assert rows[0].status == "active"
        assert rows[0].responses["messages"] == [{"role": "assistant", "content": FIRST_QUESTION}]

    @pytest.mark.asyncio
    async def test_active_session_is_resumed(self, db_session, test_user, request_client, ai):
        pid = await _project_with_pathway(db_session, test_user.id)
        history = [
            {"role": "assistant", "content": "Q1"},
            {"role": "user", "content": "A1"},
            {"role": "assistant", "content": "Q2"},
        ]
        db_session.add(
            ModuleResponse(project_id=pid, module_id=MODULE, responses={"messages": history}, status="active")
        )
        await db_session.commit()

        res = request_client.post(f"/api/v1/modules/{pid}/{MODULE}/start")

        assert res.status_code == 200, res.text
        body = res.json()
        assert body["resumed"] is True
        assert body["messages"] == history
        assert body["question_number"] == 2

    @pytest.mark.asyncio
    async def test_row_filled_by_discovery_starts_a_session_and_keeps_its_fields(
        self, db_session, test_user, request_client, ai
    ):
        """v2 discovery creates an 'active' row holding field values and no chat."""
        pid = await _project_with_pathway(db_session, test_user.id)
        db_session.add(
            ModuleResponse(
                project_id=pid,
                module_id=MODULE,
                responses={"primary_persona": "Solo founders"},
                status="active",
            )
        )
        await db_session.commit()

        res = request_client.post(f"/api/v1/modules/{pid}/{MODULE}/start")

        assert res.status_code == 200, res.text
        assert res.json()["question"] == FIRST_QUESTION
        rows = await _rows(pid)
        assert len(rows) == 1
        assert rows[0].responses["primary_persona"] == "Solo founders"
        assert len(rows[0].responses["messages"]) == 1

    @pytest.mark.asyncio
    async def test_skipped_module_can_be_started_without_a_second_row(
        self, db_session, test_user, request_client, ai
    ):
        pid = await _project_with_pathway(db_session, test_user.id)
        db_session.add(
            ModuleResponse(
                project_id=pid,
                module_id=MODULE,
                responses={"messages": [], "skipped": True},
                status="skipped",
            )
        )
        await db_session.commit()

        res = request_client.post(f"/api/v1/modules/{pid}/{MODULE}/start")

        assert res.status_code == 200, res.text
        rows = await _rows(pid)
        assert len(rows) == 1
        assert rows[0].status == "active"
        assert "skipped" not in rows[0].responses

    @pytest.mark.asyncio
    async def test_module_outside_the_pathway_is_rejected(
        self, db_session, test_user, request_client, ai
    ):
        """Control: the route still refuses a module the project never chose."""
        pid = await _project_with_pathway(db_session, test_user.id)
        await db_session.commit()

        res = request_client.post(f"/api/v1/modules/{pid}/risk_assessment/start")

        assert res.status_code == 404


class TestRespondToModule:
    @pytest.mark.asyncio
    async def test_answer_keeps_field_values_and_generated_output(
        self, db_session, test_user, request_client, ai
    ):
        pid = await _project_with_pathway(db_session, test_user.id)
        db_session.add(
            ModuleResponse(
                project_id=pid,
                module_id=MODULE,
                responses={
                    "messages": [{"role": "assistant", "content": FIRST_QUESTION}],
                    "primary_persona": "Solo founders",
                    "__generated_output": "# Persona\nSolo founders",
                },
                status="active",
            )
        )
        await db_session.commit()

        res = request_client.post(
            f"/api/v1/modules/{pid}/{MODULE}/respond", json={"content": "Founders"}
        )

        assert res.status_code == 200, res.text
        events = _sse_events(res.text)
        assert events[-1]["type"] == "done"
        assert events[-1]["complete"] is False
        stored = (await _rows(pid))[0].responses
        assert [m["role"] for m in stored["messages"]] == ["assistant", "user", "assistant"]
        assert stored["messages"][2]["content"] == "Got it. What do they struggle with?"
        assert stored["primary_persona"] == "Solo founders"
        assert stored["__generated_output"] == "# Persona\nSolo founders"
