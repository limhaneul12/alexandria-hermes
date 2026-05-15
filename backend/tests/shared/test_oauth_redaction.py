"""OAuth redaction utility behavior tests."""

from __future__ import annotations

from app.shared.util.oauth_redaction import without_oauth_sensitive_fields


def test_oauth_redaction_removes_case_and_separator_variants_recursively() -> None:
    """Redaction should hide token-shaped keys in nested objects and lists."""
    payload = {
        "accessToken": "secret-access",
        "refresh-token": "secret-refresh",
        "clientSecret": "secret-client",
        "nested": [
            {
                "device_code": "secret-device",
                "safe": "visible",
            }
        ],
        "userCode": "SECRET-CODE",
        "verificationUriComplete": "https://login.example/device?user_code=SECRET-CODE",
        "verification_uri": "https://login.example/device",
    }

    redacted = without_oauth_sensitive_fields(payload)

    assert redacted == {
        "nested": [{"safe": "visible"}],
        "verification_uri": "https://login.example/device",
    }


def test_oauth_redaction_can_keep_device_user_instructions_for_local_cli() -> None:
    """CLI OAuth start may show device-flow instructions but never tokens."""
    payload = {
        "user_code": "SECRET-CODE",
        "verification_uri_complete": "https://login.example/device?user_code=SECRET-CODE",
        "oauthAccessToken": "secret-token",
    }

    redacted = without_oauth_sensitive_fields(
        payload,
        keep_device_user_instructions=True,
    )

    assert redacted == {
        "user_code": "SECRET-CODE",
        "verification_uri_complete": "https://login.example/device?user_code=SECRET-CODE",
    }
