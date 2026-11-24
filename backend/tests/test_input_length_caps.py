"""
test_input_length_caps.py — user text forwarded to Claude has a length cap.

Finding C-3 (part): chat messages and descriptions had no length limit, so any
account could send megabytes that are then replayed to Claude on every turn.
Each route below must reject a value one character over its cap with a 422
naming the field, before the route body (and any Anthropic call) runs.

Values exactly at the cap are checked on the schemas, so the boundary is
proved without driving a full streamed chat turn.
"""
import re
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.limits import (
    BLOCK_DESCRIPTION_MAX_CHARS,
    CHAT_MESSAGE_MAX_CHARS,
    DESCRIPTION_MAX_CHARS,
)
from app.models.project import Project
from app.schemas.block import BlockCreate, BlockUpdate
from app.schemas.module_pathway import ModuleRespondPayload
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.session import MessagePayload


def _too_long_error(res, field: str) -> dict:
    """Return the 422 item for ``field``; fail unless it is a length error."""
    # Responses can echo the long input, so keep failure output short.
    assert res.status_code == 422, res.text[:300]
    items = [d for d in res.json()["detail"] if d["loc"][-1] == field]
    assert items, f"no validation error for {field!r}: {res.text[:300]}"
    assert items[0]["type"] == "string_too_long", items[0]
    return items[0]


async def _make_project(db_session, user_id) -> uuid.UUID:
    pid = uuid.uuid4()
    db_session.add(Project(id=pid, user_id=user_id, name="Capped", description="d"))
    await db_session.commit()
    return pid


class TestRoutesRejectOverLimit:
    """One character over the cap: 422 on the right field, route never runs."""

    @pytest.mark.asyncio
    async def test_discovery_message(self, request_client):
        res = request_client.post(
            f"/api/v1/discovery/{uuid.uuid4()}/message",
            json={"content": "x" * (CHAT_MESSAGE_MAX_CHARS + 1)},
        )
        item = _too_long_error(res, "content")
        assert item["ctx"]["max_length"] == CHAT_MESSAGE_MAX_CHARS

    @pytest.mark.asyncio
    async def test_discovery_message_empty(self, request_client):
        res = request_client.post(
            f"/api/v1/discovery/{uuid.uuid4()}/message", json={"content": ""}
        )
        assert res.status_code == 422, res.text
        assert res.json()["detail"][0]["type"] == "string_too_short"

    @pytest.mark.asyncio
    async def test_module_answer(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        res = request_client.post(
            f"/api/v1/modules/{pid}/core_problem/respond",
            json={"content": "x" * (CHAT_MESSAGE_MAX_CHARS + 1)},
        )
        _too_long_error(res, "content")

    @pytest.mark.asyncio
    async def test_create_project(self, request_client):
        res = request_client.post(
            "/api/v1/projects",
            json={"name": "Long", "description": "x" * (DESCRIPTION_MAX_CHARS + 1)},
        )
        item = _too_long_error(res, "description")
        assert item["ctx"]["max_length"] == DESCRIPTION_MAX_CHARS

    @pytest.mark.asyncio
    async def test_update_project(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        res = request_client.patch(
            f"/api/v1/projects/{pid}",
            json={"description": "x" * (DESCRIPTION_MAX_CHARS + 1)},
        )
        _too_long_error(res, "description")

    @pytest.mark.asyncio
    async def test_create_block(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        res = request_client.post(
            f"/api/v1/projects/{pid}/blocks",
            json={"name": "Login", "description": "x" * (BLOCK_DESCRIPTION_MAX_CHARS + 1)},
        )
        item = _too_long_error(res, "description")
        assert item["ctx"]["max_length"] == BLOCK_DESCRIPTION_MAX_CHARS

    @pytest.mark.asyncio
    async def test_update_block(self, db_session, test_user, request_client):
        pid = await _make_project(db_session, test_user.id)
        res = request_client.patch(
            f"/api/v1/projects/{pid}/blocks/{uuid.uuid4()}",
            json={"description": "x" * (BLOCK_DESCRIPTION_MAX_CHARS + 1)},
        )
        _too_long_error(res, "description")

    @pytest.mark.asyncio
    async def test_template_extra_description(self, request_client):
        res = request_client.post(
            f"/api/v1/templates/{uuid.uuid4()}/use",
            json={"extra_description": "x" * (DESCRIPTION_MAX_CHARS + 1)},
        )
        _too_long_error(res, "extra_description")

    @pytest.mark.asyncio
    async def test_pathway_detect(self, request_client):
        res = request_client.post(
            "/api/v1/pathways/detect",
            json={"description": "x" * (DESCRIPTION_MAX_CHARS + 1)},
        )
        item = _too_long_error(res, "description")
        assert item["ctx"]["max_length"] == DESCRIPTION_MAX_CHARS


class TestPathwayDetectAcceptsAFullDescription:
    """The Home page sends the same idea text to detection and to project
    creation, so detection must accept everything a description may hold.
    Otherwise a long idea silently loses pathway detection (it is best-effort
    on the client and falls back to the default)."""

    @pytest.mark.asyncio
    async def test_detect_at_description_cap(self, request_client, monkeypatch):
        calls: list[int] = []

        async def fake_detect(description: str) -> dict:
            calls.append(len(description))
            return {"pathway_id": "software_product", "confidence": 1.0}

        monkeypatch.setattr("app.routers.pathways.detect_pathway", fake_detect)
        res = request_client.post(
            "/api/v1/pathways/detect", json={"description": "x" * DESCRIPTION_MAX_CHARS}
        )
        assert res.status_code == 200, res.text
        assert calls == [DESCRIPTION_MAX_CHARS]


class TestSchemasAcceptTheCap:
    """Exactly at the cap is allowed; one over is not."""

    @pytest.mark.parametrize(
        ("make", "cap"),
        [
            (lambda s: MessagePayload(content=s), CHAT_MESSAGE_MAX_CHARS),
            (lambda s: ModuleRespondPayload(content=s), CHAT_MESSAGE_MAX_CHARS),
            (lambda s: ProjectCreate(name="n", description=s), DESCRIPTION_MAX_CHARS),
            (lambda s: ProjectUpdate(description=s), DESCRIPTION_MAX_CHARS),
            (lambda s: BlockCreate(name="n", description=s), BLOCK_DESCRIPTION_MAX_CHARS),
            (lambda s: BlockUpdate(description=s), BLOCK_DESCRIPTION_MAX_CHARS),
        ],
    )
    def test_boundary(self, make, cap):
        make("x" * cap)
        with pytest.raises(ValidationError):
            make("x" * (cap + 1))

    def test_descriptions_stay_optional(self):
        assert ProjectCreate(name="n").description is None
        assert BlockCreate(name="n").description is None


class TestFrontendMirrorsTheCaps:
    """The UI counter must use the same numbers, or it would let a user type a
    message the server then rejects (or block one it would accept)."""

    LIMITS_TS = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "inputLimits.ts"

    def _ts_constant(self, source: str, name: str) -> int:
        match = re.search(rf"export const {name}\s*=\s*([\d_]+)", source)
        assert match, f"{name} not found in {self.LIMITS_TS}"
        return int(match.group(1).replace("_", ""))

    def test_values_match(self):
        source = self.LIMITS_TS.read_text(encoding="utf-8")
        assert self._ts_constant(source, "CHAT_MESSAGE_MAX_CHARS") == CHAT_MESSAGE_MAX_CHARS
        assert self._ts_constant(source, "DESCRIPTION_MAX_CHARS") == DESCRIPTION_MAX_CHARS

    def test_parser_rejects_a_missing_constant(self):
        """Positive control: the regex must not pass on a file without the name."""
        with pytest.raises(AssertionError):
            self._ts_constant("export const OTHER = 5", "CHAT_MESSAGE_MAX_CHARS")
