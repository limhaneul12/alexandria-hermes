"""Backend application entrypoint for Alexandria Hermes."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI

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
from app.mcp_server.backend_api_client import AlexandriaApiClient, AlexandriaApiSettings
from app.mcp_server.http_auth_factory import build_mcp_http_auth_gate
from app.mcp_server.http_mount import (
    MCP_HTTP_MOUNT_PATH,
    McpHttpMount,
    mcp_streamable_http_lifespan,
)
from app.mcp_server.interface.routers.protected_resource_metadata_router import (
    router as protected_resource_metadata_router,
)
from app.memory.interface.routers.context_retrieval_router import (
    router as context_retrieval_router,
)
from app.memory.interface.routers.context_router import router as context_router
from app.memory.interface.routers.memory_compact_router import (
    router as memory_compact_router,
)
from app.obsidian.interface.routers.obsidian_librarian_execution_router import (
    router as obsidian_librarian_execution_router,
)
from app.obsidian.interface.routers.obsidian_router import router as obsidian_router
from app.obsidian.interface.routers.obsidian_settings_router import (
    router as obsidian_settings_router,
)
from app.operations.interface.routers.operational_readiness_router import (
    router as operational_readiness_router,
)
from app.operations.interface.routers.recovery_plan_router import (
    router as recovery_plan_router,
)
from app.operations.interface.routers.recovery_run_router import (
    router as recovery_run_router,
)
from app.platform.config.app_config import AppConfig
from app.platform.health_router import install_health_routes
from app.platform.lifecycle.state import LifecycleState
from app.platform.logging.formatter.config import configure_logging
from app.platform.middleware.database_session import install_database_session_middleware
from app.platform.middleware.request_logging import install_request_logging_middleware
from app.shared.infrastructure.database import Database

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
    mcp_mount = McpHttpMount(build_mcp_http_auth_gate(app_config))
    mcp_api_settings = AlexandriaApiSettings.from_env()
    mcp_api_client = AlexandriaApiClient(mcp_api_settings)

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
            async with mcp_streamable_http_lifespan(
                client=mcp_api_client,
                transport_host=app_config.mcp_transport_host,
            ) as mcp_app:
                mcp_mount.set_app(mcp_app)
                try:
                    yield
                finally:
                    mcp_mount.set_app(None)
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
    app.state.app_config = app_config

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
            "app.memory.interface.routers",
            "app.obsidian.interface.routers",
            "app.operations.interface.routers",
        ]
    )

    install_database_session_middleware(app, resolve_database=resolve_database)
    install_request_logging_middleware(app, logger=logger)
    install_health_routes(
        app,
        lifecycle=lifecycle,
        refresh_dependency_health=refresh_dependency_health,
    )
    app.include_router(protected_resource_metadata_router)
    app.mount(MCP_HTTP_MOUNT_PATH, mcp_mount)

    app.include_router(context_router)
    app.include_router(context_retrieval_router)
    app.include_router(memory_compact_router)
    app.include_router(obsidian_router)
    app.include_router(obsidian_librarian_execution_router)
    app.include_router(obsidian_settings_router)
    app.include_router(operational_readiness_router)
    app.include_router(recovery_plan_router)
    app.include_router(recovery_run_router)
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
