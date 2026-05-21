"""
encryption.py — Fernet-based encryption for external integration tokens.
Requires INTEGRATION_TOKEN_KEY to be set (base64-encoded Fernet key).
"""
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    """Get a Fernet instance from the configured key."""
    if not settings.INTEGRATION_TOKEN_KEY:
        raise RuntimeError("INTEGRATION_TOKEN_KEY is required for integration credentials")
    return Fernet(settings.INTEGRATION_TOKEN_KEY.encode("utf-8"))


def encrypt_secret(value: str | None) -> str | None:
    """Encrypt a plaintext secret. Returns None for None/empty input."""
    if not value:
        return value
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    """Decrypt an encrypted secret. Returns None if decryption fails or input is empty."""
    if not value:
        return value
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
