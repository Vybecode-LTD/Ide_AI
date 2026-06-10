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

    # Notion integration (OAuth). All three must be set for the Notion
    # connect flow to work; when any is empty the integration reports
    # "not configured" and the routes return 503 instead of breaking.
    # Register a PUBLIC integration at https://www.notion.so/my-integrations
    # and set the redirect URI to <backend-origin>/api/v1/integrations/notion/callback.
    NOTION_CLIENT_ID: str = ""
    NOTION_CLIENT_SECRET: str = ""
    NOTION_REDIRECT_URI: str = ""

    # Resend inbound email webhook verification
    RESEND_WEBHOOK_SECRET: str = ""

    # Viewer access token for password-protected shares
    SHARE_ACCESS_SECRET: str = ""

    # Per-IP rate limiting on public/anonymous endpoints (SAST-H1).
    # Disabled by the test suite so repeated test requests never 429.
    RATE_LIMIT_ENABLED: bool = True

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

    # Redis (for realtime inbox pubsub). Optional in dev — empty disables
    # realtime updates and the /inbox/stream endpoint returns 503.
    REDIS_URL: str = ""

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
