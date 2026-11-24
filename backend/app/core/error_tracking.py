"""
error_tracking.py — Sentry for the backend, off unless SENTRY_DSN is set.

Requests to this API carry people's ideas and conversations, so events carry
the error and its stack, not the data: no default personal data, no request
bodies, and no local variables from stack frames (the SDK's defaults would
attach bodies up to 10 KB, a whole chat message, and frame locals such as
prompts and emails). Log lines are not kept as breadcrumbs (some log an
email or model output). Every URL in an event loses its query string (OAuth
codes, for one) and has share-link tokens masked: a token in
``/sharing/public/<token>`` opens that shared project.

Not scrubbed: exception messages and the text of ERROR-level log calls,
which Sentry sends as events. Keep user data out of both.
"""
import re
from typing import Any

from app.core.config import Settings

_SHARE_TOKEN = re.compile(r"/(shared|sharing/public)/[^/?#]+")
_QUERY_OR_FRAGMENT = re.compile(r"[?#]")
_BREADCRUMB_URL_FIELDS = ("url", "from", "to")


def scrub_url(url: str) -> str:
    """Drop the query string and fragment, and mask share-link tokens."""
    without_query = _QUERY_OR_FRAGMENT.split(url, maxsplit=1)[0]
    return _SHARE_TOKEN.sub(r"/\1/[token]", without_query)


def scrub_breadcrumb(crumb: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Drop log-line breadcrumbs; scrub URLs in the rest."""
    if crumb.get("type") == "log":
        return None
    data = crumb.get("data")
    if isinstance(data, dict):
        for field in _BREADCRUMB_URL_FIELDS:
            if isinstance(data.get(field), str):
                data[field] = scrub_url(data[field])
        data.pop("http.query", None)
        data.pop("http.fragment", None)
    return crumb


def scrub_event(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Keep only the method and a scrubbed URL of the request; scrub breadcrumbs."""
    request = event.get("request")
    if isinstance(request, dict):
        kept: dict[str, Any] = {}
        if isinstance(request.get("method"), str):
            kept["method"] = request["method"]
        if isinstance(request.get("url"), str):
            kept["url"] = scrub_url(request["url"])
        event["request"] = kept
    breadcrumbs = event.get("breadcrumbs")
    values = breadcrumbs.get("values") if isinstance(breadcrumbs, dict) else breadcrumbs
    if isinstance(values, list):
        kept_crumbs = [c for c in values if not isinstance(c, dict) or scrub_breadcrumb(c) is not None]
        if isinstance(breadcrumbs, dict):
            breadcrumbs["values"] = kept_crumbs
        else:
            event["breadcrumbs"] = kept_crumbs
    return event


def sentry_options(settings: Settings) -> dict[str, Any]:
    """Keyword arguments for ``sentry_sdk.init``."""
    return {
        "dsn": settings.SENTRY_DSN,
        "environment": settings.ENVIRONMENT,
        "traces_sample_rate": settings.SENTRY_TRACES_SAMPLE_RATE,
        "send_default_pii": False,
        "max_request_body_size": "never",
        "include_local_variables": False,
        "before_send": scrub_event,
        "before_send_transaction": scrub_event,
        "before_breadcrumb": scrub_breadcrumb,
    }


def init_error_tracking(settings: Settings) -> bool:
    """Start Sentry when a DSN is configured. Returns whether it started."""
    if not settings.SENTRY_DSN:
        return False
    import sentry_sdk

    sentry_sdk.init(**sentry_options(settings))
    return True
