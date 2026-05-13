"""Authenticated encryption helpers for credential storage."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass

from app.platform.config.app_config import AppConfig
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_TOKEN_PREFIX = "enc:v1"
_NONCE_SIZE = 12
_LOCAL_DEV_KEY_SEED = "alexandria-hermes-local-development-secret-v1"


def _urlsafe_b64encode(value: bytes) -> str:
    """Encode bytes for compact storage."""
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _urlsafe_b64decode(value: str) -> bytes:
    """Decode unpadded URL-safe base64 text."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _derive_key(raw_key: str) -> bytes:
    """Derive a 256-bit AES key from an environment-provided key string."""
    try:
        decoded = _urlsafe_b64decode(raw_key)
    except ValueError:
        decoded = b""
    if len(decoded) == 32:
        return decoded
    return hashlib.sha256(raw_key.encode("utf-8")).digest()


@dataclass(frozen=True, slots=True)
class SecretCipher:
    """Encrypt and decrypt provider secrets before persistence.

    Args:
        key: Raw 256-bit AES-GCM key.
        allow_legacy_plaintext: Whether unresolved legacy values may be returned.
    """

    key: bytes
    allow_legacy_plaintext: bool = True

    @classmethod
    def from_app_config(cls, config: AppConfig | None = None) -> SecretCipher:
        """Build a cipher from service config.

        Local development gets a stable development key so tests and smoke runs work
        without extra setup. Stage/prod fail closed if SERVICE_SECRET_ENCRYPTION_KEY is
        missing.
        """
        app_config = AppConfig() if config is None else config
        configured_key = app_config.secret_encryption_key
        if configured_key:
            return cls(key=_derive_key(configured_key))
        if app_config.app_env == "local":
            local_seed = f"{app_config.app_name}:{_LOCAL_DEV_KEY_SEED}"
            return cls(key=_derive_key(local_seed))
        raise RuntimeError("SERVICE_SECRET_ENCRYPTION_KEY is required outside local env")

    def encrypt(self, value: str) -> str:
        """Encrypt one secret string for database storage."""
        nonce = secrets.token_bytes(_NONCE_SIZE)
        ciphertext = AESGCM(self.key).encrypt(nonce, value.encode("utf-8"), None)
        return f"{_TOKEN_PREFIX}:{_urlsafe_b64encode(nonce)}:{_urlsafe_b64encode(ciphertext)}"

    def decrypt(self, stored_value: str) -> str:
        """Decrypt one stored secret string.

        Legacy plaintext values are returned only when allow_legacy_plaintext is true.
        """
        if not stored_value.startswith(f"{_TOKEN_PREFIX}:"):
            if self.allow_legacy_plaintext:
                return stored_value
            raise ValueError("Stored secret is not encrypted")
        parts = stored_value.split(":", 3)
        if len(parts) != 4 or parts[0] != "enc" or parts[1] != "v1":
            raise ValueError("Stored secret has an invalid encrypted format")
        nonce = _urlsafe_b64decode(parts[2])
        ciphertext = _urlsafe_b64decode(parts[3])
        plaintext = AESGCM(self.key).decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
