"""Authenticated encryption helpers for credential storage."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Literal

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
class SecretCipherSettings:
    """Primitive settings needed to build the provider secret cipher."""

    app_name: str = "alexandria-hermes"
    app_env: Literal["local", "stage", "prod"] = "local"
    secret_encryption_key: str | None = None


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
    def from_settings(cls, settings: SecretCipherSettings) -> SecretCipher:
        """Build a cipher from primitive service settings.

        Local development gets a stable development key so tests and smoke runs work
        without extra setup. Stage/prod fail closed if SERVICE_SECRET_ENCRYPTION_KEY is
        missing.

        Args:
            settings: Primitive cipher settings.

        Returns:
            SecretCipher: Configured cipher.
        """
        configured_key = settings.secret_encryption_key
        if configured_key:
            return cls(key=_derive_key(configured_key))
        if settings.app_env == "local":
            local_seed = f"{settings.app_name}:{_LOCAL_DEV_KEY_SEED}"
            return cls(key=_derive_key(local_seed))
        raise RuntimeError(
            "SERVICE_SECRET_ENCRYPTION_KEY is required outside local env"
        )

    @classmethod
    def from_environment(cls) -> SecretCipher:
        """Build a cipher from SERVICE_* environment variables.

        Returns:
            SecretCipher: Configured cipher.
        """
        env_value = os.environ.get("SERVICE_APP_ENV", "local")
        if env_value not in {"local", "stage", "prod"}:
            env_value = "local"
        settings = SecretCipherSettings(
            app_name=os.environ.get("SERVICE_APP_NAME", "alexandria-hermes"),
            app_env=env_value,
            secret_encryption_key=os.environ.get("SERVICE_SECRET_ENCRYPTION_KEY"),
        )
        return cls.from_settings(settings)

    def encrypt(self, value: str) -> str:
        """Encrypt one secret string for database storage.

        Args:
            value [str]: Value supplied to encrypt.

        Returns:
            str: Value produced by encrypt.
        """
        nonce = secrets.token_bytes(_NONCE_SIZE)
        ciphertext = AESGCM(self.key).encrypt(nonce, value.encode("utf-8"), None)
        return f"{_TOKEN_PREFIX}:{_urlsafe_b64encode(nonce)}:{_urlsafe_b64encode(ciphertext)}"

    def decrypt(self, stored_value: str) -> str:
        """Decrypt one stored secret string.

        Legacy plaintext values are returned only when allow_legacy_plaintext is true.

        Args:
            stored_value [str]: Value supplied to decrypt.

        Returns:
            str: Value produced by decrypt.
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
