"""JSON logging configuration module for backend services."""

from __future__ import annotations

import logging
import traceback
from datetime import UTC, datetime
from types import TracebackType

from app.platform.config.app_config import AppConfig
from app.platform.schemas.logging_schema import (
    JsonLogError,
    JsonLogHttpContext,
    JsonLogPayload,
    JsonLogServiceContext,
    JsonLogTraceContext,
)
from app.shared.serialization.model_codec import model_to_dict
from app.shared.serialization.orjson_codec import dumps_json
from app.shared.types.extra_types import JSONObject
from app.shared.util.logging import (
    log_record_extra_float,
    log_record_extra_int,
    log_record_extra_str,
    log_record_extra_str_or_default,
)


def _should_include_error_stack(app_env: str) -> bool:
    """Decide whether error stack traces are included based on environment.

    Args:
        app_env: See function signature.

    Return:
        Return value.
    """
    return app_env.lower() in {"local", "stage", "prod"}


def _format_stack(
    *,
    exc_type: type[BaseException] | None,
    exc_value: BaseException | None,
    exc_tb: TracebackType | None,
    include_stack: bool,
) -> str:
    """Convert an exception traceback to a JSON logging string.

    Args:
        exc_type: See function signature.
        exc_value: See function signature.
        exc_tb: See function signature.
        include_stack: See function signature.

    Return:
        Return value.
    """
    if not include_stack:
        return ""
    return "".join(traceback.format_exception(exc_type, exc_value, exc_tb))


def _error_payload(
    *,
    record: logging.LogRecord,
    include_stack: bool,
) -> JsonLogError | None:
    """Build a structured error payload from a log record.

    Args:
        record: See function signature.
        include_stack: See function signature.

    Return:
        Return value.
    """
    if not record.exc_info:
        return None

    exc_type, exc_value, exc_tb = record.exc_info
    exc_type_name: str | None = None if exc_type is None else exc_type.__name__
    exc_message: str | None = None if exc_value is None else str(exc_value)

    return JsonLogError(
        type=exc_type_name,
        message=exc_message,
        stack=_format_stack(
            exc_type=exc_type,
            exc_value=exc_value,
            exc_tb=exc_tb,
            include_stack=include_stack,
        ),
    )


def _trace_context(record: logging.LogRecord) -> JsonLogTraceContext:
    """Build trace context payload from a log record.

    Args:
        record: See function signature.

    Return:
        Return value.
    """
    request_id = log_record_extra_str(record=record, key="request_id")
    return JsonLogTraceContext(
        request_id=request_id,
        correlation_id=log_record_extra_str(
            record=record,
            key="correlation_id",
            default=request_id,
        ),
        trace_id=log_record_extra_str(record=record, key="trace_id"),
    )


def _http_context(record: logging.LogRecord) -> JsonLogHttpContext:
    """Build HTTP context payload from a log record.

    Args:
        record: See function signature.

    Return:
        Return value.
    """
    return JsonLogHttpContext(
        method=log_record_extra_str(record=record, key="http_method"),
        path=log_record_extra_str(record=record, key="path"),
        status_code=log_record_extra_int(record=record, key="status_code"),
    )


def _log_payload(
    *,
    record: logging.LogRecord,
    service_context: JsonLogServiceContext,
    include_error_stack: bool,
) -> JsonLogPayload:
    """Create a validated structured Pydantic payload for one log record.

    Args:
        record: See function signature.
        service_context: See function signature.
        include_error_stack: See function signature.

    Return:
        Return value.
    """
    event_name = log_record_extra_str_or_default(
        record=record,
        key="event",
        default=record.name,
    )
    return JsonLogPayload(
        ts=datetime.now(UTC).isoformat(timespec="milliseconds"),
        level=record.levelname,
        logger=record.name,
        event=event_name,
        msg=record.getMessage(),
        func=log_record_extra_str(record=record, key="func", default=record.funcName),
        duration_ms=log_record_extra_float(record=record, key="duration_ms"),
        service=service_context,
        trace=_trace_context(record),
        http=_http_context(record),
        error=_error_payload(record=record, include_stack=include_error_stack),
    )


def _flatten_payload(payload: JsonLogPayload) -> JSONObject:
    """Flatten nested payload models into a flat dictionary for log output.

    Args:
        payload: See function signature.

    Return:
        Return value.
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

    return {
        **payload_dict,
        **service,
        **trace,
        "http_method": http.get("method"),
        "path": http.get("path"),
        "status_code": http.get("status_code"),
    }


class JsonFormatter(logging.Formatter):
    """Formatter that converts log records into machine-readable JSON."""

    def __init__(
        self,
        *,
        service_context: JsonLogServiceContext,
        include_error_stack: bool,
    ) -> None:
        """Initialize a JSON formatter instance.

        Args:
            service_context: See function signature.
            include_error_stack: See function signature.

        Return:
            None.
        """
        super().__init__()
        self._service_context = service_context
        self._include_error_stack = include_error_stack

    def format(self, record: logging.LogRecord) -> str:
        """Encode a log record as a JSON string.

        Args:
            record: See function signature.

        Return:
            Return value.
        """
        payload = _log_payload(
            record=record,
            service_context=self._service_context,
            include_error_stack=self._include_error_stack,
        )
        return dumps_json(_flatten_payload(payload)).decode("utf-8")


def _has_json_stream_handler(logger: logging.Logger) -> bool:
    """Check whether a logger already has a stream handler using JsonFormatter.

    Args:
        logger: See function signature.

    Return:
        Return value.
    """
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and isinstance(
            handler.formatter, JsonFormatter
        ):
            return True
    return False


def configure_logging() -> None:
    """Configure root logging with a JSON stream handler.

    This function directly inspects and normalizes handler state so repeated calls
    do not register duplicate handlers.

    Args:
        None.

    Return:
        None.
    """
    app_config = AppConfig()
    level_name = app_config.app_log_level.upper()
    log_level = logging.getLevelNamesMapping().get(level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    if not _has_json_stream_handler(root_logger):
        service_context = JsonLogServiceContext(
            service=app_config.app_name,
            env=app_config.app_env,
            version=app_config.app_version,
        )
        include_error_stack = _should_include_error_stack(service_context.env)
        for existing_handler in root_logger.handlers[:]:
            root_logger.removeHandler(existing_handler)
        handler = logging.StreamHandler()
        handler.setFormatter(
            JsonFormatter(
                service_context=service_context,
                include_error_stack=include_error_stack,
            )
        )
        root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(logger_name)
        for existing_handler in uvicorn_logger.handlers[:]:
            uvicorn_logger.removeHandler(existing_handler)
        uvicorn_logger.propagate = True

    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    for existing_handler in uvicorn_access_logger.handlers[:]:
        uvicorn_access_logger.removeHandler(existing_handler)
    uvicorn_access_logger.propagate = False
    uvicorn_access_logger.disabled = True
