"""
user.py — Pydantic v2 schemas for User registration, login, profile, and response.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: Optional[str] = Field(None, max_length=100)


class UserRead(BaseModel):
    """Schema for user response (excludes password)."""
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None
    email_verified: bool = False
    account_type: str = "free"
    bio: Optional[str] = None
    inbox_email: Optional[str] = None
    preferences: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    """Full user profile returned by /auth/me."""
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    oauth_provider: Optional[str] = None
    email_verified: bool = False
    account_type: str = "free"
    is_admin: bool = False
    bio: Optional[str] = None
    inbox_email: Optional[str] = None
    preferences: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VerifyEmailRequest(BaseModel):
    """Body for POST /auth/verify-email."""
    code: str = Field(min_length=6, max_length=6)


class UserProfileUpdate(BaseModel):
    """Schema for PATCH /auth/me — all fields optional."""
    name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=500)
    preferences: Optional[dict] = None


class PasswordChange(BaseModel):
    """Schema for changing password (email/password users only)."""
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token payload."""
    user_id: Optional[uuid.UUID] = None


class OAuthCodePayload(BaseModel):
    """Body sent by the frontend after OAuth redirect."""
    code: str


class ForgotPasswordRequest(BaseModel):
    """Body for POST /auth/forgot-password."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Body for POST /auth/reset-password."""
    token: str
    new_password: str = Field(min_length=8, max_length=128)
