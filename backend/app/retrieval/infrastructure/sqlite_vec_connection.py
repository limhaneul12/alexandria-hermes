"""sqlite-vec loading for async SQLite connections."""

from __future__ import annotations

from typing import cast

from aiosqlite import Connection as AioSqliteConnection
from sqlalchemy.ext.asyncio import AsyncSession


async def load_sqlite_vec_for_session(session: AsyncSession) -> None:
    """Load sqlite-vec into the active SQLAlchemy async SQLite connection.

    Args:
        session: Active async session whose connection will run vector SQL.

    Returns:
        None.
    """
    # lazy import justified: sqlite-vec is only loaded into DB connections that execute vector SQL.
    import sqlite_vec

    connection = await session.connection()
    if connection.info.get("sqlite_vec_loaded") is True:
        return
    raw_connection = await connection.get_raw_connection()
    driver_connection = cast(AioSqliteConnection, raw_connection.driver_connection)
    await driver_connection.enable_load_extension(True)
    try:
        await driver_connection.load_extension(sqlite_vec.loadable_path())
        connection.info["sqlite_vec_loaded"] = True
    finally:
        await driver_connection.enable_load_extension(False)
