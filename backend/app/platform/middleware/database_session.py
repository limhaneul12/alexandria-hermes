"""Request-scoped SQLAlchemy session middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.shared.infrastructure.database import Database
from fastapi import FastAPI
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

DatabaseResolver = Callable[[], Awaitable[Database]]


def install_database_session_middleware(
    app: FastAPI,
    *,
    resolve_database: DatabaseResolver,
) -> None:
    """Install request-scoped SQLAlchemy session management.

    Args:
        app: FastAPI application receiving the middleware.
        resolve_database: Async callable returning the application database resource.

    Returns:
        None.
    """

    @app.middleware("http")
    async def database_session_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Bind one database session to the current request context.

        Args:
            request: Incoming ASGI request.
            call_next: Next request handler in the middleware chain.

        Returns:
            Response produced by the downstream handler.
        """
        database = await resolve_database()
        async with database.request_session() as session:
            try:
                response = await call_next(request)
            except Exception:
                await session.rollback()
                raise

            if response.status_code < 400:
                await session.commit()
            else:
                await session.rollback()
            return response
