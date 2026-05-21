"""
config.py — Application settings loaded from environment variables.
Uses pydantic-settings for typed configuration with .env file support.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration. Reads from .env file and environment variables."""

    DATABASE_URL: str
    ANTHROPIC_KEY: str = ""
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    APP_NAME: str = "Ide/AI"
    FRONTEND_URL: str = "http://localhost:5173"

    # Clerk authentication
    CLERK_SECRET_KEY: str = ""
    CLERK_WEBHOOK_SECRET: str = ""
    CLERK_JWKS_URL: str = ""

    # Email — Resend
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@send.myide.ai"
    INBOX_DOMAIN: str = "inbox.myide.ai"

    # Integration token encryption
    INTEGRATION_TOKEN_KEY: str = ""

    # Resend inbound email webhook verification
    RESEND_WEBHOOK_SECRET: str = ""

    # Clerk JWT hardening (optional but recommended for production)
    CLERK_ISSUER: str = ""
    CLERK_AUDIENCE: str = ""
    CLERK_AUTHORIZED_PARTIES: list[str] = []

    # Stripe billing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_BASIC_MONTHLY: str = ""
    STRIPE_PRICE_BASIC_YEARLY: str = ""
    STRIPE_PRICE_PRO_MONTHLY: str = ""
    STRIPE_PRICE_PRO_YEARLY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def async_database_url(self) -> str:
        """Return DATABASE_URL with the asyncpg driver scheme.

        Railway provides ``postgresql://...`` but SQLAlchemy's async engine
        requires ``postgresql+asyncpg://...``. This property handles the
        conversion automatically so the raw env var works in both environments.
        """
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
