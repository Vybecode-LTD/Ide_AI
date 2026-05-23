"""
auth.py — Authentication router. Provides get_current_user dependency (Clerk JWT)
and profile management endpoints. Sign-in/sign-up/OAuth are handled by Clerk.
"""
import base64
import logging
import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clerk import verify_clerk_token
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserProfile,
    UserProfileUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


async def _fetch_clerk_email(clerk_user_id: str) -> str | None:
    """Fetch the user's primary email from Clerk Backend API."""
    if not settings.CLERK_SECRET_KEY:
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_user_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                email_addresses = data.get("email_addresses", [])
                primary_id = data.get("primary_email_address_id")
                for ea in email_addresses:
                    if ea.get("id") == primary_id:
                        return ea.get("email_address")
                if email_addresses:
                    return email_addresses[0].get("email_address")
    except Exception as exc:
        logger.warning("Failed to fetch email from Clerk API: %s", exc)
    return None


async def _link_existing_email_user(
    db: AsyncSession,
    email: str | None,
    clerk_user_id: str,
) -> User | None:
    """If a user with this email exists (e.g. webhook ran first), link the
    clerk_user_id to that row. Returns the linked user, or None if no match
    / linking failed due to a race."""
    if not email:
        return None
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing is None:
        return None

    existing.clerk_user_id = clerk_user_id
    if not existing.inbox_email:
        existing.inbox_email = f"{secrets.token_hex(4)}@{settings.INBOX_DOMAIN}"
    try:
        await db.flush()
        return existing
    except IntegrityError:
        # Another concurrent request linked the same clerk_id to a different row.
        # Roll back and let the caller re-resolve via clerk_user_id.
        await db.rollback()
        return None


async def _idempotent_create_user(
    db: AsyncSession,
    clerk_user_id: str,
    email: str | None,
) -> User | None:
    """Atomically create a user row, idempotent on clerk_user_id collisions.

    Uses PostgreSQL's INSERT ... ON CONFLICT (clerk_user_id) DO NOTHING to
    collapse the race window with the Clerk webhook. Always returns the
    canonical row by SELECT after the insert (whether we created it or not).

    Returns None only if the row still can't be found, which should be
    impossible unless the DB is in an inconsistent state.
    """
    stmt = (
        pg_insert(User)
        .values(
            clerk_user_id=clerk_user_id,
            email=email or f"{clerk_user_id}@clerk.pending",
            email_verified=True,
            inbox_email=f"{secrets.token_hex(4)}@{settings.INBOX_DOMAIN}",
            preferences={},
        )
        .on_conflict_do_nothing(index_elements=["clerk_user_id"])
    )
    try:
        await db.execute(stmt)
        await db.flush()
    except IntegrityError:
        # An OTHER unique constraint conflicted (email or inbox_email).
        # Most common: another request inserted the same email between our
        # email-link check and this insert. Roll back and re-resolve below.
        await db.rollback()

    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    return result.scalar_one_or_none()


async def get_current_user(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that extracts and validates the current user from a Clerk session JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Extract Bearer token
    if not authorization.startswith("Bearer "):
        raise credentials_exception

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise credentials_exception

    try:
        payload = verify_clerk_token(token)
        clerk_user_id: str = payload.get("sub", "")
        if not clerk_user_id:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    # Step 1: Fast path — look up by clerk_user_id
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Step 2: Webhook may not have arrived yet. Try linking an existing
        # email-only row (created by webhook) to this clerk_user_id, then
        # fall back to atomic INSERT ... ON CONFLICT DO NOTHING.
        email = await _fetch_clerk_email(clerk_user_id)
        user = await _link_existing_email_user(db, email, clerk_user_id)
        if user is not None:
            logger.info("Linked existing email user to clerk_id=%s", clerk_user_id)
        else:
            user = await _idempotent_create_user(db, clerk_user_id, email)
            if user is not None:
                logger.info("Created/resolved user via JWT path for clerk_id=%s", clerk_user_id)
        if user is None:
            # Last-ditch re-resolve by clerk_user_id, then by email
            result = await db.execute(
                select(User).where(User.clerk_user_id == clerk_user_id)
            )
            user = result.scalar_one_or_none()
            if user is None and email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user is not None and user.clerk_user_id != clerk_user_id:
                    user.clerk_user_id = clerk_user_id
                    try:
                        await db.flush()
                    except IntegrityError:
                        await db.rollback()
                        user = None
            if user is None:
                logger.error(
                    "Failed to resolve user for clerk_id=%s after upsert", clerk_user_id
                )
                raise credentials_exception

    dirty = False

    # Backfill: fix placeholder emails by fetching from Clerk API
    if user.email and ("@clerk.placeholder" in user.email or "@clerk.pending" in user.email):
        real_email = await _fetch_clerk_email(clerk_user_id)
        if real_email:
            # Check that no other user already has this email before updating
            result = await db.execute(
                select(User.id).where(User.email == real_email, User.id != user.id)
            )
            if result.scalar_one_or_none() is None:
                user.email = real_email
                dirty = True
            else:
                logger.warning(
                    "Cannot backfill email %s for user %s — already taken by another row",
                    real_email, user.id,
                )

    # Backfill: generate inbox_email if missing
    if not user.inbox_email:
        user.inbox_email = f"{secrets.token_hex(4)}@{settings.INBOX_DOMAIN}"
        dirty = True

    # Backfill: update inbox_email if on a stale domain
    if user.inbox_email and not user.inbox_email.endswith(f"@{settings.INBOX_DOMAIN}"):
        local_part = user.inbox_email.split("@")[0]
        user.inbox_email = f"{local_part}@{settings.INBOX_DOMAIN}"
        dirty = True

    if dirty:
        try:
            await db.flush()
        except IntegrityError:
            # Constraint conflict on backfill — skip it, don't crash the request
            await db.rollback()
            logger.warning("Backfill flush failed for user %s due to constraint conflict", user.id)
            # Re-query the user after rollback so we return a valid ORM instance
            result = await db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
            user = result.scalar_one_or_none()
            if user is None:
                raise credentials_exception

    return user


# ---------- Profile ----------

@router.get("/me", response_model=UserProfile)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.get("/me/entitlements")
async def get_entitlements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's plan limits and current usage."""
    from app.services.entitlement_service import get_limits, check_project_limit

    limits = get_limits(current_user)
    project_check = await check_project_limit(current_user, db)
    return {
        "plan": current_user.account_type or "free",
        "limits": limits,
        "usage": {
            "projects": project_check["current"],
        },
    }


@router.patch("/me", response_model=UserProfile)
async def update_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile fields."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    await db.flush()
    return current_user


@router.post("/me/avatar", response_model=UserProfile)
async def upload_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an avatar image (jpg/png/webp, max 2MB). Stored as base64 data URI."""
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_SIZE = 2 * 1024 * 1024  # 2MB

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be JPEG, PNG, or WebP",
        )

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be under 2MB",
        )

    b64 = base64.b64encode(content).decode("utf-8")
    data_uri = f"data:{file.content_type};base64,{b64}"

    current_user.avatar_url = data_uri
    await db.flush()
    await db.refresh(current_user)
    return current_user

