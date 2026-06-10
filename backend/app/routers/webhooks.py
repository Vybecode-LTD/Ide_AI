"""
webhooks.py — Inbound email webhook handler for Resend.
Receives emails sent to user@inbox.myide.ai and creates inbox items.

Resend delivers webhook payloads using Svix, so verification uses the
standard ``svix-id``, ``svix-timestamp``, ``svix-signature`` headers.
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.rate_limit import limiter
from app.models.idea_inbox import IdeaInbox
from app.models.user import User
from app.services import inbox_pubsub

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_resend_webhook(raw_body: bytes, headers: dict[str, str]) -> dict:
    """Verify a Resend webhook using Svix signature verification.

    Returns the parsed payload on success.
    Raises ``HTTPException(401)`` if the signature is invalid.
    """
    from svix.webhooks import Webhook, WebhookVerificationError

    if not settings.RESEND_WEBHOOK_SECRET:
        raise RuntimeError("RESEND_WEBHOOK_SECRET is required")

    wh = Webhook(settings.RESEND_WEBHOOK_SECRET)
    try:
        return wh.verify(
            raw_body.decode("utf-8"),
            {
                "svix-id": headers.get("svix-id", ""),
                "svix-timestamp": headers.get("svix-timestamp", ""),
                "svix-signature": headers.get("svix-signature", ""),
            },
        )
    except WebhookVerificationError:
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/inbound-email", status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")  # generous — Svix retries legitimately burst
async def inbound_email(request: Request):
    """
    Handle inbound email from Resend.
    Resend sends a POST with JSON body containing:
    - from: sender email
    - to: recipient (user's inbox_email)
    - subject: email subject
    - text / html: email body
    """
    # Enforce webhook signature verification in production
    if settings.ENVIRONMENT == "production" and not settings.RESEND_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Inbound email webhook secret is not configured")

    raw_body = await request.body()

    # Reject oversized payloads (max 256KB)
    if len(raw_body) > 256 * 1024:
        raise HTTPException(status_code=413, detail="Payload too large")

    # Verify signature when secret is configured; in development without a
    # secret just parse the JSON directly.
    if settings.RESEND_WEBHOOK_SECRET:
        payload = _verify_resend_webhook(raw_body, dict(request.headers))
    elif settings.ENVIRONMENT != "production":
        try:
            payload = request.scope.get("_json") or await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        raise HTTPException(status_code=500, detail="Webhook secret is required in production")

    # ── Idempotency: Svix retries carry the same svix-id header ───────
    event_id = request.headers.get("svix-id")

    # Resend wraps inbound email fields inside a "data" envelope;
    # fall back to the raw payload for backwards compatibility.
    email_data = payload.get("data") or payload

    to_email = email_data.get("to", "")
    subject = email_data.get("subject", "Untitled Idea")
    body = email_data.get("text") or email_data.get("html", "")
    sender = email_data.get("from", "")

    if not to_email:
        return {"status": "no recipient"}

    # Normalize: Resend may send to as a list or string
    if isinstance(to_email, list):
        to_email = to_email[0] if to_email else ""

    # Look up the user by inbox_email
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.inbox_email == to_email)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.info("Inbound email for unknown recipient: %s", to_email)
            return {"status": "unknown recipient"}

        # Idempotency check: skip duplicate events
        if event_id:
            existing = await db.execute(
                select(IdeaInbox.id).where(IdeaInbox.provider_event_id == event_id)
            )
            if existing.scalar_one_or_none():
                return {"status": "duplicate"}

        item = IdeaInbox(
            user_id=user.id,
            subject=subject[:500],
            body=body[:10000] if body else None,
            source="email",
            sender_email=sender[:255] if sender else None,
            provider_event_id=event_id[:255] if event_id else None,
        )
        db.add(item)
        await db.commit()
        # Refresh so we have the persisted id for the realtime event
        await db.refresh(item)

    # Publish OUTSIDE the session — pubsub is best-effort and shouldn't
    # extend the DB transaction window.
    await inbox_pubsub.publish_event(
        user.id,
        {
            "type": "added",
            "id": str(item.id),
            "subject": item.subject,
            "source": "email",
        },
    )

    return {"status": "ok"}
