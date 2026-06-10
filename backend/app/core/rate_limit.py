"""
rate_limit.py — Per-IP rate limiting via slowapi (SAST-H1).

Targets the anonymous/public surface: shared-project comments, ratings,
password verification, the inbound-email webhook, and AI-costing routes.
Authenticated app routes are NOT limited here — entitlements gate those.

Railway terminates TLS at its edge and forwards the client address in
``X-Forwarded-For``, so the key function prefers the first hop there and
falls back to the socket address for local/dev traffic.

Set ``RATE_LIMIT_ENABLED=false`` to disable (the test suite does this so
repeated requests in tests never trip a limiter).
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def client_ip(request: Request) -> str:
    """Real client IP behind the Railway edge proxy, else socket address."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=client_ip,
    enabled=settings.RATE_LIMIT_ENABLED,
    # In-memory storage: per-process counters. Fine for the current
    # single-instance Railway deployment; swap to a Redis storage URI
    # (REDIS_URL is already provisioned) if the backend ever scales out.
)
