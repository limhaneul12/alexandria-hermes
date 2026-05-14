"""Request-scoped database session middleware contracts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from app.platform.middleware.database_session import install_database_session_middleware
from app.shared.infrastructure.database import Database
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.pool import QueuePool


def test_request_session_returns_connection_to_pool_when_route_uses_unclosed_session(
    tmp_path: Path,
) -> None:
    """Route-created sessions should be closed by the request lifecycle."""
    database = Database(database_url=f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await database.initialize()
        try:
            yield
        finally:
            await database.shutdown()

    app = FastAPI(lifespan=lifespan)

    async def resolve_database() -> Database:
        return database

    install_database_session_middleware(app, resolve_database=resolve_database)

    @app.get("/uses-db")
    async def uses_db() -> dict[str, bool]:
        session = database.session()
        await session.execute(text("SELECT 1"))
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/uses-db")

        assert response.json() == {"ok": True}
        assert cast(QueuePool, database.engine.sync_engine.pool).checkedout() == 0


def test_request_session_commits_successful_route_changes(tmp_path: Path) -> None:
    """Successful responses should commit work made through the request session."""
    database = Database(database_url=f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await database.initialize()
        async with database.engine.begin() as connection:
            await connection.execute(text("CREATE TABLE messages (value TEXT)"))
        try:
            yield
        finally:
            await database.shutdown()

    app = FastAPI(lifespan=lifespan)

    async def resolve_database() -> Database:
        return database

    install_database_session_middleware(app, resolve_database=resolve_database)

    @app.post("/messages")
    async def create_message() -> dict[str, bool]:
        session = database.session()
        await session.execute(text("INSERT INTO messages (value) VALUES ('saved')"))
        return {"ok": True}

    @app.get("/message-count")
    async def message_count() -> dict[str, int]:
        session = database.session()
        count = await session.scalar(text("SELECT COUNT(*) FROM messages"))
        return {"count": int(count or 0)}

    with TestClient(app) as client:
        response = client.post("/messages")
        count_response = client.get("/message-count")

        assert response.json() == {"ok": True}
        assert count_response.json() == {"count": 1}


def test_request_session_rolls_back_failed_route_changes(tmp_path: Path) -> None:
    """Error responses should roll back work made through the request session."""
    database = Database(database_url=f"sqlite+aiosqlite:///{tmp_path / 'app.db'}")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await database.initialize()
        async with database.engine.begin() as connection:
            await connection.execute(text("CREATE TABLE messages (value TEXT)"))
        try:
            yield
        finally:
            await database.shutdown()

    app = FastAPI(lifespan=lifespan)

    async def resolve_database() -> Database:
        return database

    install_database_session_middleware(app, resolve_database=resolve_database)

    @app.post("/messages")
    async def create_message() -> dict[str, bool]:
        session = database.session()
        await session.execute(text("INSERT INTO messages (value) VALUES ('lost')"))
        raise HTTPException(status_code=400, detail="bad message")

    @app.get("/message-count")
    async def message_count() -> dict[str, int]:
        session = database.session()
        count = await session.scalar(text("SELECT COUNT(*) FROM messages"))
        return {"count": int(count or 0)}

    with TestClient(app) as client:
        response = client.post("/messages")
        count_response = client.get("/message-count")

        assert response.json() == {"detail": "bad message"}
        assert count_response.json() == {"count": 0}
