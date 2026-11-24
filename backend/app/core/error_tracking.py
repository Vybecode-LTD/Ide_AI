"""
error_tracking.py — Sentry for the backend, off unless SENTRY_DSN is set.

Requests to this API carry people's ideas and conversations, so events carry
the error and its stack, not the data: no default personal data, no request
bodies, and no local variables from stack frames (the SDK's defaults would
attach bodies up to 10 KB, a whole chat message, and frame locals such as
prompts and emails).
"""
from typing import Any

from app.core.config import Settings


def sentry_options(settings: Settings) -> dict[str, Any]:
    """Keyword arguments for ``sentry_sdk.init``."""
    return {
        "dsn": settings.SENTRY_DSN,
        "environment": settings.ENVIRONMENT,
        "traces_sample_rate": settings.SENTRY_TRACES_SAMPLE_RATE,
        "send_default_pii": False,
        "max_request_body_size": "never",
        "include_local_variables": False,
    }


def init_error_tracking(settings: Settings) -> bool:
    """Start Sentry when a DSN is configured. Returns whether it started."""
    if not settings.SENTRY_DSN:
        return False
    import sentry_sdk

    sentry_sdk.init(**sentry_options(settings))
    return True
