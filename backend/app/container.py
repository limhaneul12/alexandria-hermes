"""Application-level dependency-injector container."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from app.connections.containers import ConnectionsContainer
from app.librarian.containers import LibrarianContainer
from app.memory.containers import MemoryContainer
from app.obsidian.containers import ObsidianContainer
from app.platform.config.app_config import AppConfig
from app.platform.config.database_config import DatabaseConfig
from app.shared.infrastructure.database import Database
from app.shared.security.secret_cipher import SecretCipher, SecretCipherSettings


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


def create_secret_cipher(config: AppConfig) -> SecretCipher:
    """Create the provider secret cipher from typed service settings.

    Args:
        config: Typed service configuration.

    Returns:
        SecretCipher: Configured credential cipher.
    """
    settings = SecretCipherSettings(
        app_name=config.app_name,
        app_env=config.app_env,
        secret_encryption_key=config.secret_encryption_key,
    )
    cipher = SecretCipher.from_settings(settings)
    return cipher


class ApplicationContainer(containers.DeclarativeContainer):
    """Root container for shared application resources."""

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.connections.interface.routers",
            "app.librarian.interface.routers",
            "app.memory.interface.routers",
            "app.obsidian.interface.routers",
        ],
    )

    app_config = providers.Singleton(AppConfig)
    secret_cipher = providers.Singleton(create_secret_cipher, config=app_config)
    database_config = providers.Singleton(DatabaseConfig)
    database = providers.Resource(
        initialize_database,
        database_url=database_config.provided.url,
    )
    db_session = providers.Factory(create_session, database=database)

    memory = providers.Container(
        MemoryContainer,
        db_session=db_session,
        app_config=app_config,
    )
    connections = providers.Container(
        ConnectionsContainer,
        db_session=db_session,
        secret_cipher=secret_cipher,
    )
    librarian = providers.Container(
        LibrarianContainer,
        db_session=db_session,
        librarian_provider_repo=connections.librarian_provider_repo,
        provider_secret_repo=connections.provider_secret_repo,
        memory_compact_service=memory.memory_compact_service,
    )
    obsidian = providers.Container(
        ObsidianContainer,
        db_session=db_session,
        database=database,
        app_config=app_config,
        librarian_delegate_service=librarian.hermes_collaboration_service,
    )
