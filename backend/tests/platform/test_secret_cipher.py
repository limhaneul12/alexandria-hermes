"""Secret cipher behavior tests."""

from __future__ import annotations

from typing import Literal

import pytest
from app.platform.config.app_config import AppConfig
from app.shared.security.secret_cipher import SecretCipher


def _app_config(
    *,
    app_env: Literal["local", "stage", "prod"] = "local",
    secret_encryption_key: str | None = None,
) -> AppConfig:
    return AppConfig(
        app_env=app_env,
        secret_encryption_key=secret_encryption_key,
        codex_oauth_issuer="https://auth.openai.com",
        codex_oauth_client_id="app_EMoamEEZ73f0CkXaXp7hrann",
        codex_oauth_device_expires_in_seconds=900,
        codex_oauth_min_poll_interval_seconds=3,
    )


def test_secret_cipher_encrypts_without_plaintext_and_round_trips() -> None:
    """SecretCipher should hide plaintext while preserving resolvability."""
    cipher = SecretCipher.from_app_config(
        _app_config(
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
        SecretCipher.from_app_config(_app_config(app_env="prod"))
