"""
clerk_webhook.py — Handles Clerk webhook events for user sync.
Verifies webhook signatures using svix and syncs user data to the local database.
"""
import logging
import secrets

from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User


def _generate_inbox_email() -> str:
    """Generate a unique inbox email address for a user."""
    local_part = secrets.token_hex(4)  # 8 hex chars
    return f"{local_part}@{settings.INBOX_DOMAIN}"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _verify_webhook(payload: bytes, headers: dict) -> dict:
    """Verify Clerk webhook signature using svix and return parsed payload."""
    from svix.webhooks import Webhook

    wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
    try:
        data = wh.verify(payload, headers)
    except Exception as e:
        logger.error("Webhook signature verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        )
    return data


@router.post("/clerk", status_code=status.HTTP_200_OK)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Process Clerk webhook events for user lifecycle management."""
    payload = await request.body()
    headers = {
        "svix-id": request.headers.get("svix-id", ""),
        "svix-timestamp": request.headers.get("svix-timestamp", ""),
        "svix-signature": request.headers.get("svix-signature", ""),
    }

    data = _verify_webhook(payload, headers)
    event_type = data.get("type", "")
    user_data = data.get("data", {})

    logger.info("Clerk webhook received: %s", event_type)

    try:
        if event_type == "user.created":
            await _handle_user_created(user_data, db)
        elif event_type == "user.updated":
            await _handle_user_updated(user_data, db)
        elif event_type == "user.deleted":
            await _handle_user_deleted(user_data, db)
    except Exception as e:
        logger.error("Error handling Clerk webhook %s: %s", event_type, e, exc_info=True)
        raise

    return {"status": "ok"}


async def _handle_user_created(user_data: dict, db: AsyncSession) -> None:
    """Create a local user row from Clerk user data."""
    clerk_id = user_data.get("id", "")
    email = _extract_primary_email(user_data)

    if not email:
        logger.warning("No email found in Clerk user data for %s", clerk_id)
        return

    # First check by clerk_id (most specific)
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_id)
    )
    existing = result.scalars().first()

    if existing:
        # Already linked — just update name (don't overwrite custom display_name)
        existing.name = _build_full_name(user_data) or existing.name
        existing.email_verified = True
        if user_data.get("image_url"):
            existing.avatar_url = user_data["image_url"]
        await db.flush()
        logger.info("Updated existing Clerk-linked user: %s", email)
        return

    # Then check by email
    result = await db.execute(
        select(User).where(User.email == email)
    )
    existing_by_email = result.scalars().first()

    if existing_by_email:
        # Link existing email user to Clerk
        existing_by_email.clerk_user_id = clerk_id
        existing_by_email.name = _build_full_name(user_data) or existing_by_email.name
        existing_by_email.email_verified = True
        if user_data.get("image_url") and not existing_by_email.avatar_url:
            existing_by_email.avatar_url = user_data["image_url"]
        if not existing_by_email.inbox_email:
            existing_by_email.inbox_email = _generate_inbox_email()
        await db.flush()
        logger.info("Linked existing user to Clerk: %s", email)
        return

    # No existing user — create new
    user = User(
        email=email,
        clerk_user_id=clerk_id,
        name=_build_full_name(user_data),
        display_name=_build_display_name(user_data),
        avatar_url=user_data.get("image_url"),
        email_verified=True,
        inbox_email=_generate_inbox_email(),
        preferences={},
    )
    db.add(user)
    await db.flush()
    logger.info("Created new user from Clerk: %s", email)


async def _handle_user_updated(user_data: dict, db: AsyncSession) -> None:
    """Update local user row from Clerk user data."""
    clerk_id = user_data.get("id", "")
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_id)
    )
    user = result.scalars().first()

    if not user:
        # User doesn't exist locally yet — create them
        await _handle_user_created(user_data, db)
        return

    email = _extract_primary_email(user_data)
    if email and email != user.email:
        # Only update email if no other user already has it
        conflict = await db.execute(
            select(User.id).where(User.email == email, User.id != user.id)
        )
        if conflict.scalar_one_or_none() is None:
            user.email = email
        else:
            logger.warning("Cannot update email to %s for user %s — already taken", email, user.id)

    full_name = _build_full_name(user_data)
    if full_name:
        user.name = full_name
    # Don't overwrite display_name on updates — user may have customized it

    if user_data.get("image_url"):
        user.avatar_url = user_data["image_url"]

    await db.flush()
    logger.info("Updated user from Clerk: %s", email)


async def _handle_user_deleted(user_data: dict, db: AsyncSession) -> None:
    """Deactivate user when deleted from Clerk. Preserves data for billing/audit."""
    clerk_id = user_data.get("id", "")
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_id)
    )
    user = result.scalars().first()

    if user:
        user.clerk_user_id = None
        await db.flush()
        logger.info("Deactivated Clerk user: %s", clerk_id)


def _extract_primary_email(user_data: dict) -> str:
    """Extract the primary email from Clerk user data."""
    email_addresses = user_data.get("email_addresses", [])
    primary_id = user_data.get("primary_email_address_id")

    for ea in email_addresses:
        if ea.get("id") == primary_id:
            return ea.get("email_address", "")

    if email_addresses:
        return email_addresses[0].get("email_address", "")

    return ""


def _build_full_name(user_data: dict) -> str:
    """Build a full name (first + last) from Clerk user data."""
    first = user_data.get("first_name") or ""
    last = user_data.get("last_name") or ""
    return f"{first} {last}".strip()


def _build_display_name(user_data: dict) -> str:
    """Build a display name (first name only) from Clerk user data."""
    return (user_data.get("first_name") or "").strip()
