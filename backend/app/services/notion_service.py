"""
notion_service.py — Notion OAuth + design-kit push.

Two responsibilities, kept deliberately separate so the pure logic is unit-
testable without the network:

  1. **OAuth helpers** (`is_configured`, `build_authorize_url`,
     `exchange_code_for_token`) — wrap Notion's 3-legged OAuth. Only
     `exchange_code_for_token` does IO.
  2. **Design-kit rendering** (`render_design_kit_blocks`) — a *pure* function
     that turns a unified artifact context (see
     ``artifact_context_service.build_artifact_context``) into a list of Notion
     block objects. No network, fully testable.
  3. **Notion API IO** (`create_design_kit_page`, `list_accessible_pages`) —
     thin httpx wrappers over the Notion REST API.

When the three ``NOTION_*`` settings are unset the integration is "not
configured": ``is_configured()`` returns False and the routes return 503 rather
than breaking. The whole flow goes live the moment those env vars are set.
"""
from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
NOTION_AUTHORIZE_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

# Notion API limits we have to respect.
_MAX_RICH_TEXT = 2000  # characters per rich-text object
_MAX_CHILDREN = 100  # blocks per create / append request
_HTTP_TIMEOUT = 30.0


# ── Configuration ────────────────────────────────────────────────────────────


def is_configured() -> bool:
    """True only when all three OAuth settings are present."""
    return bool(
        settings.NOTION_CLIENT_ID
        and settings.NOTION_CLIENT_SECRET
        and settings.NOTION_REDIRECT_URI
    )


# ── OAuth ────────────────────────────────────────────────────────────────────


def build_authorize_url(state: str) -> str:
    """Build the Notion authorize URL the browser is redirected to.

    ``state`` is a signed token (minted by the router) that we verify on the
    callback to bind the redirect back to the originating user.
    """
    params = {
        "client_id": settings.NOTION_CLIENT_ID,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": settings.NOTION_REDIRECT_URI,
        "state": state,
    }
    return f"{NOTION_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """Exchange an authorization code for an access token.

    Notion uses HTTP Basic auth (client_id:client_secret) on the token
    endpoint; the secret never touches the browser. Returns the raw token
    payload (``access_token``, ``workspace_id``, ``workspace_name``,
    ``workspace_icon``, ``bot_id``, ...).

    Raises ``httpx.HTTPStatusError`` on a non-2xx response so the caller can
    surface a clean error.
    """
    basic = base64.b64encode(
        f"{settings.NOTION_CLIENT_ID}:{settings.NOTION_CLIENT_SECRET}".encode("utf-8")
    ).decode("utf-8")

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            NOTION_TOKEN_URL,
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/json",
                "Notion-Version": NOTION_VERSION,
            },
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.NOTION_REDIRECT_URI,
            },
        )
    resp.raise_for_status()
    return resp.json()


# ── Block rendering (pure) ───────────────────────────────────────────────────


def _value_text(value: Any) -> str:
    """Render an arbitrary field value to a human-readable single string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ", ".join(_value_text(v) for v in value if v not in (None, "", [], {}))
    if isinstance(value, dict):
        parts = [f"{k}: {_value_text(v)}" for k, v in value.items() if v not in (None, "", [], {})]
        return "; ".join(parts)
    return str(value)


def _rich_text(content: str) -> list[dict]:
    """Build a Notion rich_text array, truncating to the per-object limit."""
    text = (content or "")[:_MAX_RICH_TEXT]
    if not text:
        return []
    return [{"type": "text", "text": {"content": text}}]


def _heading(level: int, content: str) -> dict:
    htype = f"heading_{max(1, min(3, level))}"
    return {"object": "block", "type": htype, htype: {"rich_text": _rich_text(content)}}


def _paragraph(content: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich_text(content)}}


def _bullet(content: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rich_text(content)},
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def render_design_kit_blocks(context: dict[str, Any]) -> list[dict]:
    """Turn a unified artifact context into a list of Notion block objects.

    Pure function — no network, no DB. Works for both flow versions:
      - v2 projects render their ``modules`` (label + filled field values).
      - v1 projects render the design-sheet fields (problem / mvp / features /
        constraints / success metric).
    Both render the shared ``blocks`` (feature board) and ``pipeline`` (tech
    stack) sections when present.
    """
    blocks: list[dict] = []

    # ── Header ──
    name = context.get("project_name") or "Untitled Project"
    blocks.append(_heading(1, name))
    if context.get("project_description"):
        blocks.append(_paragraph(context["project_description"]))

    # ── At-a-glance ──
    meta_bits = []
    for key, label in (("platform", "Platform"), ("audience", "Audience"),
                       ("tone", "Tone"), ("complexity", "Complexity")):
        val = context.get(key)
        if val:
            meta_bits.append(f"{label}: {val}")
    if meta_bits:
        blocks.append(_divider())
        for bit in meta_bits:
            blocks.append(_bullet(bit))

    flow_version = context.get("flow_version", "v1")

    if flow_version == "v2":
        modules = context.get("modules") or []
        rendered_any = False
        for mod in modules:
            responses = mod.get("responses") or {}
            field_schemas = {f.get("key"): f for f in (mod.get("fields") or []) if f.get("key")}
            # Collect non-empty, non-internal fields for this module.
            lines: list[tuple[str, str]] = []
            for key, value in responses.items():
                if key.startswith("__"):  # __generated_output etc.
                    continue
                text = _value_text(value)
                if not text:
                    continue
                schema = field_schemas.get(key, {})
                lines.append((schema.get("label") or key, text))
            if not lines:
                continue
            rendered_any = True
            blocks.append(_divider())
            blocks.append(_heading(2, mod.get("label") or mod.get("module_id") or "Module"))
            for label, text in lines:
                blocks.append(_bullet(f"{label}: {text}"))
        if not rendered_any and context.get("discovery_summary"):
            blocks.append(_divider())
            blocks.append(_heading(2, "Discovery Summary"))
            blocks.append(_paragraph(context["discovery_summary"]))
    else:
        # v1 design-sheet fields.
        sheet_fields = [
            ("problem", "Problem"),
            ("mvp", "MVP Scope"),
            ("tech_constraints", "Tech Constraints"),
            ("success_metric", "Success Metric"),
        ]
        present = [(k, lbl) for k, lbl in sheet_fields if context.get(k)]
        if present:
            blocks.append(_divider())
            blocks.append(_heading(2, "Design Sheet"))
            for key, label in present:
                blocks.append(_bullet(f"{label}: {_value_text(context[key])}"))
        features = context.get("features") or []
        if features:
            blocks.append(_heading(3, "Features"))
            for feat in features:
                blocks.append(_bullet(_value_text(feat)))

    # ── Feature blocks board (shared) ──
    feature_blocks = context.get("blocks") or []
    if feature_blocks:
        blocks.append(_divider())
        blocks.append(_heading(2, "Feature Blocks"))
        for b in feature_blocks:
            name = getattr(b, "name", None) or (b.get("name") if isinstance(b, dict) else None)
            if not name:
                continue
            priority = getattr(b, "priority", None) or (b.get("priority") if isinstance(b, dict) else "")
            effort = getattr(b, "effort", None) or (b.get("effort") if isinstance(b, dict) else "")
            tag = " · ".join(x for x in (priority, f"effort {effort}" if effort else "") if x)
            label = f"{name}" + (f"  ({tag})" if tag else "")
            blocks.append(_bullet(label))

    # ── Pipeline / tech stack (shared) ──
    pipeline = context.get("pipeline") or []
    if pipeline:
        blocks.append(_divider())
        blocks.append(_heading(2, "Tech Stack"))
        for node in pipeline:
            layer = getattr(node, "layer", None) or (node.get("layer") if isinstance(node, dict) else None)
            tool = getattr(node, "selected_tool", None) or (node.get("selected_tool") if isinstance(node, dict) else None)
            if layer and tool:
                blocks.append(_bullet(f"{layer}: {tool}"))

    blocks.append(_divider())
    blocks.append(_paragraph("Generated by Ide/AI — myide.ai"))

    return blocks


def _chunk(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


# ── Notion API IO ────────────────────────────────────────────────────────────


def _api_headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


async def list_accessible_pages(access_token: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return pages the integration can write to, as ``[{id, title}]``.

    Used to populate the parent-page picker. Notion's search returns pages the
    integration has been explicitly shared with.
    """
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{NOTION_API_BASE}/search",
            headers=_api_headers(access_token),
            json={
                "filter": {"property": "object", "value": "page"},
                "page_size": min(limit, 100),
            },
        )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    pages: list[dict[str, Any]] = []
    for page in results:
        pages.append({"id": page.get("id"), "title": _extract_page_title(page)})
    return pages


def _extract_page_title(page: dict[str, Any]) -> str:
    """Pull a human-readable title out of a Notion page object."""
    props = page.get("properties", {}) or {}
    for prop in props.values():
        if prop.get("type") == "title":
            title_arr = prop.get("title", [])
            if title_arr:
                return "".join(t.get("plain_text", "") for t in title_arr) or "Untitled"
    return "Untitled"


async def create_design_kit_page(
    access_token: str,
    parent_page_id: str,
    title: str,
    blocks: list[dict],
) -> dict[str, Any]:
    """Create a Notion page under ``parent_page_id`` with the given blocks.

    Notion caps a create request at 100 children, so the first 100 blocks go in
    the create call and any overflow is appended in batches. Returns
    ``{"id": <page id>, "url": <page url>}``.
    """
    first, *rest_batches = _chunk(blocks, _MAX_CHILDREN) or [[]]

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{NOTION_API_BASE}/pages",
            headers=_api_headers(access_token),
            json={
                "parent": {"type": "page_id", "page_id": parent_page_id},
                "properties": {
                    "title": {"title": _rich_text(title)},
                },
                "children": first,
            },
        )
        resp.raise_for_status()
        page = resp.json()
        page_id = page.get("id")

        # Append any overflow batches.
        for batch in rest_batches:
            append_resp = await client.patch(
                f"{NOTION_API_BASE}/blocks/{page_id}/children",
                headers=_api_headers(access_token),
                json={"children": batch},
            )
            append_resp.raise_for_status()

    return {"id": page_id, "url": page.get("url", "")}
