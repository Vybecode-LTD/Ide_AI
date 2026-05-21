"""
auth.py — Authentication router. Provides get_current_user dependency (Clerk JWT)
and profile management endpoints. Sign-in/sign-up/OAuth are handled by Clerk.
"""
import base64
import secrets

from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clerk import verify_clerk_token
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserProfile,
    UserProfileUpdate,
)

router = APIRouter(prefix="/auth", tags=["auth"])


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

    # Look up local user by clerk_user_id
    result = await db.execute(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        # On-first-request fallback: create user row if webhook hasn't arrived yet
        user = User(
            clerk_user_id=clerk_user_id,
            email=payload.get("email", f"{clerk_user_id}@clerk.placeholder"),
            email_verified=True,
            inbox_email=f"{secrets.token_hex(4)}@{settings.INBOX_DOMAIN}",
            preferences={},
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

    # Backfill inbox_email for users created before this feature
    if not user.inbox_email:
        user.inbox_email = f"{secrets.token_hex(4)}@{settings.INBOX_DOMAIN}"
        await db.flush()

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

