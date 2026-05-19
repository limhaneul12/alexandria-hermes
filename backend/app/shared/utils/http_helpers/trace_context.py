"""HTTP request trace and endpoint resolution helpers."""

from __future__ import annotations

from types import FunctionType, MethodType
from uuid import uuid4

from fastapi import Request


def resolve_request_id(request: Request) -> str:
    """Read or generate the request identifier.

    Args:
        request: Incoming HTTP request.

    Returns:
        Request ID used for the request lifecycle.
    """
    request_id = request.headers.get("x-request-id")
    if request_id:
        return request_id

    correlation_id = request.headers.get("x-correlation-id")
    if correlation_id:
        return correlation_id

    generated_request_id = str(uuid4())
    return generated_request_id


def resolve_trace_context(request: Request) -> str:
    """Resolve trace ID from request headers.

    Priority:
        1. x-trace-id
        2. Auto-generated UUID per request

    Args:
        request: Incoming HTTP request.

    Returns:
        Trace ID string.
    """
    trace_id = request.headers.get("x-trace-id")
    if trace_id:
        return trace_id

    generated_trace_id = str(uuid4())
    return generated_trace_id


def resolve_endpoint_name(request: Request) -> str | None:
    """Find the fully-qualified endpoint function name from request scope.

    Args:
        request: Incoming HTTP request.

    Returns:
        Fully-qualified endpoint function name, or None if unavailable.
    """
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return None

    if isinstance(endpoint, FunctionType | MethodType):
        endpoint_name = f"{endpoint.__module__}.{endpoint.__qualname__}"
        return endpoint_name

    return None
