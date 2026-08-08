"""Memory and lifecycle contracts for the Redis maintenance worker."""

from __future__ import annotations

from inspect import getsource

import pytest
from app.operations.workers.redis_maintenance_worker import (
    _create_worker_container,
    run_worker,
)
from app.platform.config.maintenance_queue_config import MaintenanceQueueConfig


def test_worker_container_defers_unrelated_process_resources() -> None:
    """Worker construction must not eagerly allocate API Redis or Neo4j clients."""
    config = MaintenanceQueueConfig(_env_file=None).model_copy(
        update={"embedding_threads": 1}
    )
    container = _create_worker_container(config)

    assert container.app_config().rag_embedding_threads == 1
    assert container.memory.graph_signal_provider() is None
    assert container.database.initialized is False
    assert container.redis_client.initialized is False
    assert container.graph_projection_repository.initialized is False


def test_worker_startup_does_not_initialize_every_application_resource() -> None:
    """The worker should initialize only resources reached by the reindex path."""
    assert "init_resources" not in getsource(run_worker)


def test_worker_embedding_threads_are_loaded_from_dedicated_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Worker CPU concurrency should not reuse the API embedding-thread setting."""
    monkeypatch.setenv("SERVICE_RAG_MAINTENANCE_EMBEDDING_THREADS", "2")

    config = MaintenanceQueueConfig(_env_file=None)

    assert config.embedding_threads == 2
