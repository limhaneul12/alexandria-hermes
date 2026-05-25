"""Alembic environment for Alexandria-Hermes backend migrations."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

import app.connections.infrastructure.models.librarian_provider_models as _librarian_provider_models  # noqa: F401
import app.librarian.infrastructure.models.agent_models as _agent_models  # noqa: F401
import app.librarian.infrastructure.models.skill_acquisition_job_models as _skill_acquisition_job_models  # noqa: F401
import app.memory.infrastructure.models.context_models as _context_models  # noqa: F401
import app.obsidian.infrastructure.models.obsidian_index_models as _obsidian_index_models  # noqa: F401
from alembic import context
from app.shared.infrastructure.database import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without opening a live database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations on an existing sync connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through its sync bridge."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
