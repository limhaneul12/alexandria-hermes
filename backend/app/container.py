"""Application-level dependency-injector container."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.library.containers import LibraryContainer
from app.platform.config.app_config import AppConfig
from app.platform.config.database_config import DatabaseConfig
from app.shared.infrastructure.database import Database
from dependency_injector import containers, providers


@asynccontextmanager
async def initialize_database(*, database_url: str) -> AsyncGenerator[Database]:
    """Provision Database with startup/shutdown lifecycle.

    Args:
        database_url: Async SQLAlchemy database URL.

    Yield:
        Initialized Database instance.
    """
    database = Database(database_url=database_url)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


class ApplicationContainer(containers.DeclarativeContainer):
    """Root container for shared application resources."""

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.library.interface.routers",
            "app.library.interface.routers.dependencies",
        ],
    )

    app_config = providers.Singleton(AppConfig)
    database_config = providers.Singleton(DatabaseConfig)
    database = providers.Resource(
        initialize_database,
        database_url=database_config.provided.url,
    )
    db_session = providers.Factory(database.provided.session)

    library = providers.Container(
        LibraryContainer,
        db_session=db_session,
    )
