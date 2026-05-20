"""Backend application entrypoint for Alexandria Hermes."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import cast

from app.connections.interface.routers.librarian_oauth_router import (
    router as librarian_oauth_router,
)
from app.connections.interface.routers.librarian_router import (
    router as librarian_router,
)
from app.container import ApplicationContainer
from app.librarian.interface.routers.agent_router import router as agent_router
from app.librarian.interface.routers.librarian_brief_router import (
    router as librarian_brief_router,
)
from app.librarian.interface.routers.librarian_ops_router import (
    router as librarian_ops_router,
)
from app.library.interface.routers.category_router import router as category_router
from app.library.interface.routers.item_router import router as item_router
from app.library.interface.routers.item_search_router import (
    router as item_search_router,
)
from app.library.interface.routers.prompt_router import router as prompt_router
from app.library.interface.routers.skill_router import router as skill_router
from app.library.interface.routers.usage_router import router as usage_router
from app.memory.interface.routers.context_router import router as context_router
from app.memory.interface.routers.memory_compact_router import (
    router as memory_compact_router,
)
from app.platform.config.app_config import AppConfig
from app.platform.health_router import install_health_routes
from app.platform.lifecycle.state import LifecycleState
from app.platform.logging.formatter.config import configure_logging
from app.platform.middleware.database_session import install_database_session_middleware
from app.platform.middleware.request_logging import install_request_logging_middleware
from app.shared.infrastructure.database import Database
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def _docs_urls(app_env: str) -> tuple[str | None, str | None, str | None]:
    """Return docs endpoint paths based on the current environment.

    Args:
        app_env: Current app environment.

    Returns:
        Tuple for docs URL, redoc URL, and OpenAPI URL.
    """
    if app_env == "local":
        return "/docs", "/redoc", "/openapi.json"
    return None, None, None


def create_app(app_config: AppConfig) -> FastAPI:
    """Build the FastAPI application and wire core runtime dependencies.

    Args:
        app_config: Application configuration values.

    Returns:
        Configured FastAPI app.
    """
    lifecycle = LifecycleState()
    container = ApplicationContainer()

    async def refresh_dependency_health() -> None:
        """Refresh dependency health before serving readiness requests.

        Args:
            None.

        Returns:
            None.
        """
        database = await cast(Awaitable[Database], container.database())
        if await database.ping():
            lifecycle.mark_database_healthy()
        else:
            lifecycle.mark_database_unavailable()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        """Start and stop shared application resources.

        Args:
            _app: Active FastAPI app instance.

        Returns:
            Async lifecycle context.
        """
        configure_logging()
        await cast(Awaitable[None], container.init_resources())
        database = await cast(Awaitable[Database], container.database())
        lifecycle.mark_database_starting()
        if await database.ping():
            lifecycle.mark_database_healthy()
        else:
            lifecycle.mark_database_unavailable()
        lifecycle.mark_running()
        try:
            yield
        finally:
            await cast(Awaitable[None], container.shutdown_resources())
            lifecycle.mark_stopping()

    docs_url, redoc_url, openapi_url = _docs_urls(app_config.app_env)
    app = FastAPI(
        title="Alexandria Hermes API",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        version=app_config.app_version,
    )

    app.state.lifecycle = lifecycle
    app.state.container = container

    async def resolve_database() -> Database:
        """Resolve the lifecycle-owned database resource for request middleware.

        Returns:
            Active application database resource.
        """
        database = await cast(Awaitable[Database], container.database())
        return database

    container.wire(
        packages=[
            "app.connections.interface.routers",
            "app.librarian.interface.routers",
            "app.library.interface.routers",
            "app.memory.interface.routers",
        ]
    )

    install_database_session_middleware(app, resolve_database=resolve_database)
    install_request_logging_middleware(app, logger=logger)
    install_health_routes(
        app,
        lifecycle=lifecycle,
        refresh_dependency_health=refresh_dependency_health,
    )

    app.include_router(category_router)
    app.include_router(context_router)
    app.include_router(memory_compact_router)
    app.include_router(item_router)
    app.include_router(item_search_router)
    app.include_router(skill_router)
    app.include_router(prompt_router)
    app.include_router(usage_router)
    app.include_router(agent_router)
    app.include_router(librarian_router)
    app.include_router(librarian_oauth_router)
    app.include_router(librarian_ops_router)
    app.include_router(librarian_brief_router)

    @app.get("/")
    def root() -> dict[str, str]:
        """Return service metadata for quick readiness checks.

        Args:
            None.

        Returns:
            Service metadata object.
        """
        return {
            "service": app_config.app_name,
            "version": app_config.app_version,
            "status": "ok",
        }

    return app


app = create_app(AppConfig())


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
