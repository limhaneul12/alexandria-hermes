"""Secret cipher behavior tests."""

from __future__ import annotations

from typing import Literal

import pytest
from app.shared.security.secret_cipher import SecretCipher, SecretCipherSettings


def _cipher_settings(
    *,
    app_env: Literal["local", "stage", "prod"] = "local",
    secret_encryption_key: str | None = None,
) -> SecretCipherSettings:
    return SecretCipherSettings(
        app_env=app_env,
        secret_encryption_key=secret_encryption_key,
    )


def test_secret_cipher_encrypts_without_plaintext_and_round_trips() -> None:
    """SecretCipher should hide plaintext while preserving resolvability."""
    cipher = SecretCipher.from_settings(
        _cipher_settings(
            app_env="local",
            secret_encryption_key="test-encryption-key",
        )
    )

    encrypted = cipher.encrypt("do-not-store-plain")

    assert encrypted.startswith("enc:v1:")
    assert "do-not-store-plain" not in encrypted
    assert cipher.decrypt(encrypted) == "do-not-store-plain"


def test_secret_cipher_requires_configured_key_outside_local_env() -> None:
    """Stage/prod should fail closed without an explicit encryption key."""
    with pytest.raises(RuntimeError, match="SERVICE_SECRET_ENCRYPTION_KEY"):
        SecretCipher.from_settings(_cipher_settings(app_env="prod"))
