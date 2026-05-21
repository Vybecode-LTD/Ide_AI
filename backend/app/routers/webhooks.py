"""
webhooks.py — Inbound email webhook handler for Resend.
Receives emails sent to user@inbox.myide.ai and creates inbox items.
"""
import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.idea_inbox import IdeaInbox
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_resend_signature(raw_body: bytes, signature: str | None) -> bool:
    """Verify Resend webhook HMAC signature if secret is configured."""
    if not settings.RESEND_WEBHOOK_SECRET:
        return True  # No secret configured — skip verification (dev only)
    if not signature:
        return False
    expected = hmac.new(
        settings.RESEND_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/inbound-email", status_code=status.HTTP_200_OK)
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
        return {"status": "payload too large"}

    # Verify signature when secret is configured
    signature = request.headers.get("resend-signature") or request.headers.get("svix-signature")
    if settings.RESEND_WEBHOOK_SECRET and not _verify_resend_signature(raw_body, signature):
        logger.warning("Inbound email webhook: invalid signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = request.scope.get("_json") or await request.json()
    except Exception:
        return {"status": "invalid payload"}

    to_email = payload.get("to", "")
    subject = payload.get("subject", "Untitled Idea")
    body = payload.get("text") or payload.get("html", "")
    sender = payload.get("from", "")

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

        item = IdeaInbox(
            user_id=user.id,
            subject=subject[:500],
            body=body[:10000] if body else None,
            source="email",
            sender_email=sender[:255] if sender else None,
        )
        db.add(item)
        await db.commit()

    return {"status": "ok"}
