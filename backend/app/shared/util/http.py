"""Common helper module for HTTP request and tracing utilities."""

from __future__ import annotations

import logging
from types import FunctionType, MethodType
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import Request, status as http_status
from fastapi.responses import Response

if TYPE_CHECKING:  # pragma: no cover
    from app.platform.lifecycle.state import LifecycleSnapshot

HEALTHCHECK_PATHS = {"/health/live", "/health/ready", "/health/heartbeat"}


def should_skip_request_log(path: str, status_code: int) -> bool:
    """Decide whether to skip request logging.

    Args:
        path: Request path without query string.
        status_code: HTTP response status code.

    Return:
        True when the request should be skipped (healthcheck handling rule).
    """
    return path in HEALTHCHECK_PATHS and (status_code < 500 or status_code == 503)


def resolve_request_id(request: Request) -> str:
    """Read or generate the request identifier.

    Args:
        request: Incoming HTTP request.

    Return:
        Request ID used for the request lifecycle.
    """
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id

    correlation_id = request.headers.get("x-correlation-id")
    if correlation_id:
        return correlation_id

    return str(uuid4())


def resolve_trace_context(request: Request) -> str:
    """Resolve trace ID from request headers.

    Priority:
        1. x-trace-id
        2. Auto-generated UUID per request

    Args:
        request: Incoming HTTP request.

    Return:
        Trace ID string.
    """
    trace_id = request.headers.get("x-trace-id")
    if trace_id:
        return trace_id
    return str(uuid4())


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

    Return:
        None.
    """
    logger.log(
        level,
        message,
        extra={
            "event": event,
            "request_id": request_id,
            "correlation_id": request_id,
            "trace_id": trace_id,
            "http_method": http_method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "func": func,
        },
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

    Return:
        None.
    """
    del error
    logger.exception(
        message,
        extra={
            "event": event,
            "request_id": request_id,
            "correlation_id": request_id,
            "trace_id": trace_id,
            "http_method": http_method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "func": func,
        },
    )


def resolve_endpoint_name(request: Request) -> str | None:
    """Find the fully-qualified endpoint function name from request scope.

    Args:
        request: Incoming HTTP request.

    Return:
        Fully-qualified endpoint function name, or None if unavailable.
    """
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return None

    if isinstance(endpoint, FunctionType | MethodType):
        return f"{endpoint.__module__}.{endpoint.__qualname__}"

    return None


def response_headers(*, request_id: str, trace_id: str) -> dict[str, str]:
    """Build response headers for request and trace identifiers.

    Args:
        request_id: See function signature.
        trace_id: See function signature.

    Return:
        Return value.
    """
    headers = {"x-request-id": request_id}
    headers["x-trace-id"] = trace_id
    return headers


def apply_response_headers(
    *,
    response: Response,
    request_id: str,
    trace_id: str,
) -> None:
    """Attach request and trace headers to the response object.

    Args:
        response: See function signature.
        request_id: See function signature.
        trace_id: See function signature.

    Return:
        None.
    """
    for key, value in response_headers(
        request_id=request_id,
        trace_id=trace_id,
    ).items():
        response.headers[key] = value


def request_log_metadata(
    *,
    response: Response,
) -> tuple[int, str, str]:
    """Determine request log level and event name based on response status.

    Args:
        response: See function signature.

    Return:
        Return value.
    """
    if response.status_code >= 500:
        return (
            logging.ERROR,
            "request_server_error",
            "request completed with server error",
        )
    return logging.INFO, "request_completed", "request completed"


def json_response(payload: bytes, status_code: int) -> Response:
    """Wrap serialized JSON bytes into an application/json Response.

    Args:
        payload: See function signature.
        status_code: See function signature.

    Return:
        Return value.
    """
    return Response(
        content=payload,
        status_code=status_code,
        media_type="application/json",
    )


def status_code_from_snapshot(snapshot: LifecycleSnapshot) -> int:
    """Determine HTTP status code from a readiness snapshot.

    Args:
        snapshot: See function signature.

    Return:
        Return value.
    """
    if snapshot.ready:
        return http_status.HTTP_200_OK
    return http_status.HTTP_503_SERVICE_UNAVAILABLE
