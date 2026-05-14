"""Pure payload construction and shaping for JSON log records."""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime
from types import TracebackType

from app.platform.schemas.logging_schema import (
    JsonLogError,
    JsonLogHttpContext,
    JsonLogPayload,
    JsonLogServiceContext,
    JsonLogTraceContext,
)
from app.shared.serialization.model_codec import model_to_dict
from app.shared.types.extra_types import JSONObject
from app.shared.util.logging import (
    log_record_extra_float,
    log_record_extra_int,
    log_record_extra_str,
    log_record_extra_str_or_default,
    redact_sensitive_text,
)


def should_include_error_stack(app_env: str) -> bool:
    """Decide whether error stack traces are included based on environment.

    Args:
        app_env: Application environment name.

    Returns:
        Whether stack traces should be emitted.
    """
    should_include_stack = app_env.lower() in {"local", "stage", "prod"}
    return should_include_stack


def format_error_stack(
    *,
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: TracebackType | None,
    include_stack: bool,
) -> str:
    """Convert an exception traceback to a redacted JSON logging string.

    Args:
        exc_type: Exception type from ``LogRecord.exc_info``.
        exc_value: Exception value from ``LogRecord.exc_info``.
        exc_tb: Traceback from ``LogRecord.exc_info``.
        include_stack: Whether stack traces are enabled for the environment.

    Returns:
        Redacted stack text, or an empty string when disabled.
    """
    if not include_stack:
        return ""
    stack_text = redact_sensitive_text(
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    )
    formatted_stack = stack_text or ""
    return formatted_stack


def build_error_payload(
    *,
    record: logging.LogRecord,
    include_stack: bool,
) -> JsonLogError | None:
    """Build a structured error payload from a log record.

    Args:
        record: Python logging record.
        include_stack: Whether stack traces are enabled for the environment.

    Returns:
        Structured error payload when exception info is present.
    """
    if not record.exc_info:
        return None

    exc_type, exc_value, exc_tb = record.exc_info
    exc_type_name: str | None = None if exc_type is None else exc_type.__name__
    exc_message: str | None = None
    if exc_value is not None:
        exc_message = redact_sensitive_text(str(exc_value))

    error_payload = JsonLogError(
        type=exc_type_name,
        message=exc_message,
        stack=format_error_stack(
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_tb,
            include_stack=include_stack,
        ),
    )
    return error_payload


def build_trace_context(record: logging.LogRecord) -> JsonLogTraceContext:
    """Build trace context payload from a log record.

    Args:
        record: Python logging record.

    Returns:
        Structured trace context.
    """
    request_id = log_record_extra_str(record=record, key="request_id")
    trace_context = JsonLogTraceContext(
        request_id=request_id,
        correlation_id=log_record_extra_str(
            record=record,
            key="correlation_id",
            default=request_id,
        ),
        trace_id=log_record_extra_str(record=record, key="trace_id"),
    )
    return trace_context


def build_http_context(record: logging.LogRecord) -> JsonLogHttpContext:
    """Build HTTP context payload from a log record.

    Args:
        record: Python logging record.

    Returns:
        Structured HTTP context.
    """
    http_context = JsonLogHttpContext(
        method=log_record_extra_str(record=record, key="http_method"),
        path=log_record_extra_str(record=record, key="path"),
        status_code=log_record_extra_int(record=record, key="status_code"),
    )
    return http_context


def build_log_payload(
    *,
    record: logging.LogRecord,
    service_context: JsonLogServiceContext,
    include_error_stack: bool,
) -> JsonLogPayload:
    """Create a validated structured Pydantic payload for one log record.

    Args:
        record: Python logging record.
        service_context: Service context to attach to the log event.
        include_error_stack: Whether stack traces are enabled for the environment.

    Returns:
        Validated structured log payload.
    """
    event_name = log_record_extra_str_or_default(
        record=record,
        key="event",
        default=record.name,
    )
    log_payload = JsonLogPayload(
        ts=datetime.now(UTC).isoformat(timespec="milliseconds"),
        level=record.levelname,
        logger=record.name,
        event=event_name,
        msg=redact_sensitive_text(record.getMessage()) or "",
        func=log_record_extra_str(record=record, key="func", default=record.funcName),
        duration_ms=log_record_extra_float(record=record, key="duration_ms"),
        service=service_context,
        trace=build_trace_context(record),
        http=build_http_context(record),
        error=build_error_payload(record=record, include_stack=include_error_stack),
    )
    return log_payload


def flatten_log_payload(payload: JsonLogPayload) -> JSONObject:
    """Flatten nested payload models into a flat dictionary for log output.

    Args:
        payload: Structured log payload.

    Returns:
        JSON-compatible flat log object.
    """
    payload_dict = model_to_dict(payload)
    service = payload_dict.pop("service", {})
    trace = payload_dict.pop("trace", {})
    http = payload_dict.pop("http", {})

    if not isinstance(service, dict):
        service = {}
    if not isinstance(trace, dict):
        trace = {}
    if not isinstance(http, dict):
        http = {}

    flattened_payload: JSONObject = {
        **payload_dict,
        **service,
        **trace,
        "http_method": http.get("method"),
        "path": http.get("path"),
        "status_code": http.get("status_code"),
    }
    return flattened_payload
