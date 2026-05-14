"""Structured HTTP request logging helpers."""

from __future__ import annotations

import logging

from fastapi.responses import Response

HEALTHCHECK_PATHS = {"/health/live", "/health/ready", "/health/heartbeat"}


def should_skip_request_log(path: str, status_code: int) -> bool:
    """Decide whether to skip request logging.

    Args:
        path: Request path without query string.
        status_code: HTTP response status code.

    Returns:
        True when the request should be skipped (healthcheck handling rule).
    """
    skip_request_log = path in HEALTHCHECK_PATHS and (
        status_code < 500 or status_code == 503
    )
    return skip_request_log


def request_log_metadata(
    *,
    response: Response,
) -> tuple[int, str, str]:
    """Determine request log level and event name based on response status.

    Args:
        response: See function signature.

    Returns:
        Return value.
    """
    if response.status_code >= 500:
        metadata = (
            logging.ERROR,
            "request_server_error",
            "request completed with server error",
        )
        return metadata

    metadata = logging.INFO, "request_completed", "request completed"
    return metadata


def request_log_extra(
    *,
    event: str,
    request_id: str,
    http_method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    func: str | None,
    trace_id: str,
) -> dict[str, str | int | float | None]:
    """Build the structured log extra payload for a request.

    Args:
        event: See function signature.
        request_id: See function signature.
        http_method: See function signature.
        path: See function signature.
        status_code: See function signature.
        duration_ms: See function signature.
        func: See function signature.
        trace_id: See function signature.

    Returns:
        Structured logging extra fields.
    """
    extra = {
        "event": event,
        "request_id": request_id,
        "correlation_id": request_id,
        "trace_id": trace_id,
        "http_method": http_method,
        "path": path,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "func": func,
    }
    return extra


def log_request_outcome(
    logger: logging.Logger,
    *,
    level: int,
    message: str,
    event: str,
    request_id: str,
    http_method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    func: str | None,
    trace_id: str,
) -> None:
    """Log a successful request outcome as a structured record.

    Args:
        logger: See function signature.
        level: See function signature.
        message: See function signature.
        event: See function signature.
        request_id: See function signature.
        http_method: See function signature.
        path: See function signature.
        status_code: See function signature.
        duration_ms: See function signature.
        func: See function signature.
        trace_id: See function signature.

    Returns:
        None.
    """
    logger.log(
        level,
        message,
        extra=request_log_extra(
            event=event,
            request_id=request_id,
            http_method=http_method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            func=func,
            trace_id=trace_id,
        ),
    )


def log_request_exception(
    logger: logging.Logger,
    *,
    message: str,
    event: str,
    request_id: str,
    http_method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    func: str | None,
    trace_id: str,
    error: Exception,
) -> None:
    """Log a request failure with an attached exception as a structured record.

    Args:
        logger: See function signature.
        message: See function signature.
        event: See function signature.
        request_id: See function signature.
        http_method: See function signature.
        path: See function signature.
        status_code: See function signature.
        duration_ms: See function signature.
        func: See function signature.
        trace_id: See function signature.
        error: See function signature.

    Returns:
        None.
    """
    del error
    logger.exception(
        message,
        extra=request_log_extra(
            event=event,
            request_id=request_id,
            http_method=http_method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            func=func,
            trace_id=trace_id,
        ),
    )
