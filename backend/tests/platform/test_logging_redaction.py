"""Structured logging redaction regression tests."""

from __future__ import annotations

import json
import logging
import sys

from app.platform.logging.formatter.config import JsonFormatter
from app.platform.schemas.logging_schema import JsonLogServiceContext


def _formatter() -> JsonFormatter:
    """Return a formatter with stack traces enabled for redaction coverage."""
    return JsonFormatter(
        service_context=JsonLogServiceContext(
            service="alexandria-hermes",
            env="local",
            version="test",
        ),
        include_error_stack=True,
    )


def test_json_formatter_redacts_secret_values_in_messages_and_exceptions() -> None:
    """JSON formatter should not serialize secret values from log text."""
    logger_name = "tests.platform.logging_redaction"
    logger = logging.getLogger(logger_name)

    try:
        raise RuntimeError(
            "provider failed api_key=do-not-log-api-key "
            "oauth_access_token=do-not-log-token "
            "oauth_refresh_token=do-not-log-refresh-token "
            "device_code=do-not-log-device-code user_code=do-not-log-user-code "
            "Authorization: Bearer do-not-log-bearer"
        )
    except RuntimeError:
        record = logger.makeRecord(
            logger_name,
            logging.ERROR,
            __file__,
            1,
            "request failed password=do-not-log-password",
            args=(),
            exc_info=sys.exc_info(),
        )

    encoded = _formatter().format(record)
    payload = json.loads(encoded)

    assert "do-not-log-api-key" not in encoded
    assert "do-not-log-token" not in encoded
    assert "do-not-log-refresh-token" not in encoded
    assert "do-not-log-device-code" not in encoded
    assert "do-not-log-user-code" not in encoded
    assert "do-not-log-bearer" not in encoded
    assert "do-not-log-password" not in encoded
    assert payload["msg"] == "request failed password=<redacted>"
    assert payload["error"]["message"] == (
        "provider failed api_key=<redacted> oauth_access_token=<redacted> "
        "oauth_refresh_token=<redacted> device_code=<redacted> "
        "user_code=<redacted> "
        "Authorization: Bearer <redacted>"
    )
    assert "api_key=<redacted>" in payload["error"]["stack"]
