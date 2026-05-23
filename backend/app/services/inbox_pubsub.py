"""
inbox_pubsub.py — Redis pub/sub for realtime inbox events.

Each user has a channel ``inbox:user:{user_id}``. The inbox router publishes
events on create/promote/delete; the inbox webhook publishes on inbound email.
The ``/inbox/stream`` SSE endpoint subscribes to the channel for the current
user and pushes events down to the browser.

Graceful degradation: when ``REDIS_URL`` is not configured, ``publish_event``
is a no-op and ``is_available()`` returns False — the stream endpoint will
respond 503 and the frontend falls back to polling.
"""
import json
import logging
import uuid
from typing import Any, AsyncIterator

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client = None  # Lazy-initialized redis.asyncio.Redis


def is_available() -> bool:
    """Return True when REDIS_URL is configured."""
    return bool(settings.REDIS_URL)


def _channel(user_id: uuid.UUID) -> str:
    return f"inbox:user:{user_id}"


async def _get_client():
    """Return a shared redis client, lazy-initialized on first use.

    Reuses a single client/connection pool for all publishers. Subscribers
    create their own pubsub objects via ``client.pubsub()``.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not settings.REDIS_URL:
        return None
    try:
        import redis.asyncio as redis  # type: ignore
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        return _redis_client
    except Exception as exc:
        logger.warning("Failed to initialize Redis client: %s", exc)
        return None


async def publish_event(user_id: uuid.UUID, event: dict[str, Any]) -> None:
    """Publish an inbox event to the user's channel. No-op if Redis is unavailable."""
    client = await _get_client()
    if client is None:
        return
    try:
        await client.publish(_channel(user_id), json.dumps(event, default=str))
    except Exception as exc:
        logger.warning("inbox_pubsub.publish failed: %s", exc)


async def subscribe(user_id: uuid.UUID) -> AsyncIterator[dict[str, Any]]:
    """Async generator yielding events for the user. Closes cleanly on cancel.

    Raises RuntimeError if Redis is not configured — caller should check
    ``is_available()`` first and respond 503 to the client.
    """
    client = await _get_client()
    if client is None:
        raise RuntimeError("Redis is not configured")

    pubsub = client.pubsub()
    channel = _channel(user_id)
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            raw = message.get("data")
            if raw is None:
                continue
            try:
                yield json.loads(raw)
            except (TypeError, ValueError):
                logger.warning("Malformed inbox event payload: %r", raw)
    finally:
        try:
            await pubsub.unsubscribe(channel)
        finally:
            await pubsub.close()
