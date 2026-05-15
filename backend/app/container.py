"""Application-level dependency-injector container."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from app.archive.containers import ArchiveContainer
from app.connections.containers import ConnectionsContainer
from app.librarian.containers import LibrarianContainer
from app.library.containers import LibraryContainer
from app.memory.containers import MemoryContainer
from app.platform.config.app_config import AppConfig
from app.platform.config.database_config import DatabaseConfig
from app.shared.infrastructure.database import Database


@asynccontextmanager
async def initialize_database(*, database_url: str) -> AsyncGenerator[Database]:
    """Provision Database with startup/shutdown lifecycle.

    Args:
        database_url [str]: Async SQLAlchemy database URL used to create the resource.

    Yields:
        Database: Initialized database resource for the application lifecycle.
    """
    database = Database(database_url=database_url)
    await database.initialize()
    try:
        yield database
    finally:
        await database.shutdown()


def create_session(database: Database) -> AsyncSession:
    """Create a request-local async SQLAlchemy session from Database.

    Args:
        database [Database]: Value supplied to create_session.

    Returns:
        AsyncSession: Value produced by create_session.
    """
    return database.session()


class ApplicationContainer(containers.DeclarativeContainer):
    """Root container for shared application resources."""

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.archive.interface.routers",
            "app.connections.interface.routers",
            "app.librarian.interface.routers",
            "app.library.interface.routers",
            "app.memory.interface.routers",
            "app.retrieval.interface.routers",
        ],
    )

    app_config = providers.Singleton(AppConfig)
    database_config = providers.Singleton(DatabaseConfig)
    database = providers.Resource(
        initialize_database,
        database_url=database_config.provided.url,
    )
    db_session = providers.Factory(create_session, database=database)

    library = providers.Container(
        LibraryContainer,
        db_session=db_session,
    )
    memory = providers.Container(
        MemoryContainer,
        db_session=db_session,
    )
    connections = providers.Container(
        ConnectionsContainer,
        db_session=db_session,
    )
    librarian = providers.Container(
        LibrarianContainer,
        db_session=db_session,
    )
    archive = providers.Container(
        ArchiveContainer,
        db_session=db_session,
        item_service=library.item_service,
    )
