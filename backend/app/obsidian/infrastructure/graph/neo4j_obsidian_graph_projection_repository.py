"""Async Neo4j adapter for the rebuildable Obsidian graph projection."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from types import TracebackType
from typing import Concatenate, ParamSpec, Protocol, TypedDict, TypeVar

from app.obsidian.domain.contracts.obsidian_graph_projection_contracts import (
    ObsidianGraphContextEvidence,
    ObsidianGraphContextSignalType,
    ObsidianGraphDirection,
    ObsidianGraphProjection,
    ObsidianGraphProjectionEdge,
    ObsidianGraphProjectionIssueCode,
    ObsidianGraphProjectionIssueCount,
    ObsidianGraphProjectionNode,
    ObsidianGraphProjectionState,
    ObsidianGraphRelatedNote,
)
from app.obsidian.domain.event_enum.obsidian_enums import (
    AlexandriaNoteType,
    ObsidianEdgeSourceKind,
    ObsidianRelationType,
)
from app.obsidian.domain.repositories.obsidian_graph_projection_repository import (
    IObsidianGraphProjectionRepository,
)
from app.obsidian.infrastructure.graph.neo4j_graph_projection_queries import (
    ACTIVATE_PROJECTION_METADATA,
    CREATE_NOTE_KEY_CONSTRAINT,
    CREATE_PROJECTION_NAME_CONSTRAINT,
    DELETE_PROJECTION_RUN_NODES,
    READ_CONTEXT_EVIDENCE,
    READ_EDGES,
    READ_NODES,
    READ_PROJECTION_METADATA,
    READ_RELATED_NOTES,
    UPSERT_EDGES,
    UPSERT_NODES,
)

PROJECTION_NAME = "obsidian"


class Neo4jProjectionRawRow(TypedDict, total=False):
    """Validated subset of scalar fields returned by projection queries."""

    note_id: str | None
    relative_path: str
    alexandria_type: str
    title: str
    status: str
    project: str | None
    edge_id: str
    source_note_id: str
    source_path: str
    target_note_id: str | None
    target_path: str
    relation: str
    confidence: float
    source_kind: str
    run_id: str | None
    projection_version: int | None
    related_note_id: str
    direction: str
    score: float
    target_title: str
    signal: str
    issue_total: int | None
    issue_counts_json: str | None


class Neo4jProjectionRunParameters(TypedDict):
    """Projection metadata parameters shared across write statements."""

    projection_name: str
    projection_version: int
    run_id: str


class Neo4jProjectionActivationParameters(Neo4jProjectionRunParameters):
    """Projection activation parameters including last-run diagnostics."""

    issue_total: int
    issue_counts_json: str


class Neo4jProjectionNodeParameters(TypedDict):
    """One non-secret node parameter row for an UNWIND batch."""

    projection_key: str
    note_id: str
    relative_path: str
    alexandria_type: str
    title: str
    status: str
    project: str | None


class Neo4jProjectionEdgeParameters(TypedDict):
    """One non-secret relationship parameter row for an UNWIND batch."""

    edge_id: str
    source_key: str
    source_note_id: str
    source_path: str
    target_key: str
    target_note_id: str | None
    target_path: str
    relation: str
    confidence: float
    source_kind: str


Neo4jProjectionParameter = (
    str
    | int
    | float
    | bool
    | None
    | list[Neo4jProjectionNodeParameters]
    | list[Neo4jProjectionEdgeParameters]
    | list[str]
)
_P = ParamSpec("_P")
_R = TypeVar("_R")


class Neo4jProjectionResult(Protocol):
    """Narrow async result behavior consumed by this adapter."""

    async def data(self) -> list[Neo4jProjectionRawRow]:
        """Return result records as typed mappings.

        Returns:
            Scalar projection result rows.
        """

    # Broad type justified: the adapter discards the driver's version-specific
    # ResultSummary and only requires completion of result consumption.
    async def consume(self) -> object:
        """Consume the result before another query runs in the transaction.

        Returns:
            Driver-specific summary ignored by this adapter.
        """


class Neo4jProjectionTransaction(Protocol):
    """Narrow transaction behavior consumed by transaction callbacks."""

    async def run(
        self,
        query: str,
        **parameters: Neo4jProjectionParameter,
    ) -> Neo4jProjectionResult:
        """Execute one parameterized Cypher statement.

        Args:
            query: Static Cypher template.
            parameters: Non-secret values bound to named Cypher parameters.

        Returns:
            Async query result wrapper.
        """


class Neo4jProjectionSession(Protocol):
    """Short-lived async session behavior used by one repository operation."""

    async def __aenter__(self) -> Neo4jProjectionSession:
        """Enter the session context.

        Returns:
            Active operation-local session.
        """

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the session context.

        Args:
            exc_type: Raised exception type, when present.
            exc: Raised exception, when present.
            traceback: Raised exception traceback, when present.
        """

    async def execute_write(
        self,
        callback: Callable[
            Concatenate[Neo4jProjectionTransaction, _P],
            Awaitable[_R],
        ],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _R:
        """Execute an idempotent write callback with driver-managed retries.

        Args:
            callback: Retry-safe transaction callback.
            args: Positional callback arguments.
            kwargs: Named callback arguments.

        Returns:
            Callback result.
        """

    async def execute_read(
        self,
        callback: Callable[
            Concatenate[Neo4jProjectionTransaction, _P],
            Awaitable[_R],
        ],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _R:
        """Execute a read callback.

        Args:
            callback: Read transaction callback.
            args: Positional callback arguments.
            kwargs: Named callback arguments.

        Returns:
            Callback result.
        """


class Neo4jProjectionDriver(Protocol):
    """One application-lifetime async Neo4j driver."""

    def session(self, *, database: str | None = None) -> Neo4jProjectionSession:
        """Create one operation-local async session.

        Args:
            database: Explicit Neo4j database name.

        Returns:
            New short-lived async session.
        """

    async def close(self) -> None:
        """Close the application-lifetime driver."""

    async def verify_connectivity(self) -> None:
        """Verify connectivity only when explicitly requested."""


class Neo4jObsidianGraphProjectionRepository(IObsidianGraphProjectionRepository):
    """Project Obsidian graph snapshots into optional Neo4j state."""

    def __init__(
        self,
        *,
        driver: Neo4jProjectionDriver,
        database: str,
    ) -> None:
        """Create an adapter around one application-lifetime async driver.

        Args:
            driver: Shared async driver; sessions are never shared.
            database: Neo4j database selected for projection operations.
        """
        self._driver = driver
        self._database = database

    async def verify_connectivity(self) -> None:
        """Perform the explicit opt-in driver connectivity probe."""
        await self._driver.verify_connectivity()

    async def close(self) -> None:
        """Await closure of the application-lifetime async driver."""
        await self._driver.close()

    async def start_rebuild(self, *, run_id: str, projection_version: int) -> None:
        """Prepare a clean run-scoped staging area.

        Args:
            run_id: Stable application-owned run id.
            projection_version: Projection contract version being written.
        """
        del projection_version
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(_ensure_constraints)
            await session.execute_write(_delete_projection_run, run_id)

    async def write_rebuild_batch(
        self,
        *,
        run_id: str,
        projection_version: int,
        batch: ObsidianGraphProjection,
    ) -> None:
        """Stage one bounded run-scoped batch without activating it.

        Args:
            run_id: Stable application-owned run id.
            projection_version: Projection contract version being written.
            batch: Bounded projection batch to stage.
        """
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(
                _upsert_projection,
                batch,
                run_id,
                projection_version,
            )

    async def complete_rebuild(
        self,
        *,
        run_id: str,
        projection_version: int,
        issue_counts: tuple[ObsidianGraphProjectionIssueCount, ...] = (),
    ) -> None:
        """Atomically activate a staged run and delete superseded graph state.

        Args:
            run_id: Stable application-owned run id.
            projection_version: Projection contract version being activated.
        """
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(
                _activate_projection,
                run_id,
                projection_version,
                issue_counts,
            )

    async def abort_rebuild(self, *, run_id: str) -> None:
        """Delete nodes staged by a failed run.

        Args:
            run_id: Stable application-owned run id to clean up.
        """
        async with self._driver.session(database=self._database) as session:
            await session.execute_write(_delete_projection_run, run_id)

    async def state(self) -> ObsidianGraphProjectionState:
        """Read active metadata and its deterministic typed snapshot.

        Returns:
            Active projection state or explicit never-built state.
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.execute_read(_read_projection_state)
        if not isinstance(result, ObsidianGraphProjectionState):
            raise TypeError("Neo4j projection read returned an invalid result")
        return result

    async def related_notes(
        self,
        *,
        note_id: str,
        limit: int,
    ) -> tuple[ObsidianGraphRelatedNote, ...]:
        """Read ranked one-hop relations from the active projection run.

        Args:
            note_id: Stable note id whose neighbors should be expanded.
            limit: Maximum number of related notes to return.

        Returns:
            Ranked active-run relations mapped from Neo4j rows.
        """
        async with self._driver.session(database=self._database) as session:
            result = await session.execute_read(_read_related_notes, note_id, limit)
        if not isinstance(result, tuple):
            raise TypeError("Neo4j related-note read returned an invalid result")
        return result

    async def context_evidence(
        self,
        *,
        note_ids: tuple[str, ...],
    ) -> tuple[ObsidianGraphContextEvidence, ...]:
        """Read active-run graph evidence limited to recalled context ids.

        Args:
            note_ids: Recalled context ids allowed to appear in evidence.

        Returns:
            Typed active-run evidence whose endpoints are both allowed.
        """
        if not note_ids:
            return ()
        async with self._driver.session(database=self._database) as session:
            result = await session.execute_read(_read_context_evidence, note_ids)
        if not isinstance(result, tuple):
            raise TypeError("Neo4j context evidence read returned an invalid result")
        return result


async def _ensure_constraints(transaction: Neo4jProjectionTransaction) -> None:
    await (await transaction.run(CREATE_NOTE_KEY_CONSTRAINT)).consume()
    await (await transaction.run(CREATE_PROJECTION_NAME_CONSTRAINT)).consume()


async def _upsert_projection(
    transaction: Neo4jProjectionTransaction,
    projection: ObsidianGraphProjection,
    run_id: str,
    projection_version: int,
) -> None:
    run_parameters = _run_parameters(run_id, projection_version)
    await (
        await transaction.run(
            UPSERT_NODES,
            nodes=[_node_parameters(node, run_id=run_id) for node in projection.nodes],
            **run_parameters,
        )
    ).consume()
    await (
        await transaction.run(
            UPSERT_EDGES,
            edges=[_edge_parameters(edge, run_id=run_id) for edge in projection.edges],
            **run_parameters,
        )
    ).consume()


async def _delete_projection_run(
    transaction: Neo4jProjectionTransaction, run_id: str
) -> None:
    await (
        await transaction.run(
            DELETE_PROJECTION_RUN_NODES,
            projection_name=PROJECTION_NAME,
            run_id=run_id,
        )
    ).consume()


async def _activate_projection(
    transaction: Neo4jProjectionTransaction,
    run_id: str,
    projection_version: int,
    issue_counts: tuple[ObsidianGraphProjectionIssueCount, ...],
) -> None:
    parameters = _activation_parameters(run_id, projection_version, issue_counts)
    await (await transaction.run(ACTIVATE_PROJECTION_METADATA, **parameters)).consume()


async def _read_projection_state(
    transaction: Neo4jProjectionTransaction,
) -> ObsidianGraphProjectionState:
    metadata_result = await transaction.run(
        READ_PROJECTION_METADATA,
        projection_name=PROJECTION_NAME,
    )
    metadata_rows = await metadata_result.data()
    await metadata_result.consume()
    metadata: Neo4jProjectionRawRow = metadata_rows[0] if metadata_rows else {}
    run_id = _optional_text(metadata, "run_id")
    version = metadata.get("projection_version")
    if run_id is None:
        return ObsidianGraphProjectionState(initialized=False)
    if not isinstance(version, int):
        raise TypeError("Neo4j projection metadata requires integer version")
    issue_total = metadata.get("issue_total")
    if issue_total is not None and not isinstance(issue_total, int):
        raise TypeError("Neo4j projection metadata issue_total must be integer")
    issue_counts = _issue_counts_from_json(
        _optional_text(metadata, "issue_counts_json")
    )
    node_result = await transaction.run(
        READ_NODES,
        projection_name=PROJECTION_NAME,
        run_id=run_id,
    )
    node_rows = await node_result.data()
    await node_result.consume()
    edge_result = await transaction.run(
        READ_EDGES,
        projection_name=PROJECTION_NAME,
        run_id=run_id,
    )
    edge_rows = await edge_result.data()
    await edge_result.consume()
    return ObsidianGraphProjectionState(
        initialized=True,
        run_id=run_id,
        projection_version=version,
        issue_total=issue_total or 0,
        issue_counts=issue_counts,
        projection=ObsidianGraphProjection(
            nodes=tuple(_node_from_row(row) for row in node_rows),
            edges=tuple(_edge_from_row(row) for row in edge_rows),
        ),
    )


async def _read_related_notes(
    transaction: Neo4jProjectionTransaction,
    note_id: str,
    limit: int,
) -> tuple[ObsidianGraphRelatedNote, ...]:
    query_result = await transaction.run(
        READ_RELATED_NOTES,
        projection_name=PROJECTION_NAME,
        note_id=note_id,
        limit=limit,
    )
    rows = await query_result.data()
    await query_result.consume()
    return tuple(_related_note_from_row(row) for row in rows)


async def _read_context_evidence(
    transaction: Neo4jProjectionTransaction,
    note_ids: tuple[str, ...],
) -> tuple[ObsidianGraphContextEvidence, ...]:
    query_result = await transaction.run(
        READ_CONTEXT_EVIDENCE,
        projection_name=PROJECTION_NAME,
        note_ids=list(note_ids),
    )
    rows = await query_result.data()
    await query_result.consume()
    return tuple(_context_evidence_from_row(row) for row in rows)


def _run_parameters(
    run_id: str, projection_version: int
) -> Neo4jProjectionRunParameters:
    return {
        "projection_name": PROJECTION_NAME,
        "projection_version": projection_version,
        "run_id": run_id,
    }


def _activation_parameters(
    run_id: str,
    projection_version: int,
    issue_counts: tuple[ObsidianGraphProjectionIssueCount, ...],
) -> Neo4jProjectionActivationParameters:
    return {
        **_run_parameters(run_id, projection_version),
        "issue_total": sum(item.count for item in issue_counts),
        "issue_counts_json": json.dumps(
            {item.code.value: item.count for item in issue_counts},
            separators=(",", ":"),
            sort_keys=True,
        ),
    }


def _issue_counts_from_json(
    value: str | None,
) -> tuple[ObsidianGraphProjectionIssueCount, ...]:
    if value is None:
        return ()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise TypeError("Neo4j projection issue summary must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise TypeError("Neo4j projection issue summary must be an object")
    counts: list[ObsidianGraphProjectionIssueCount] = []
    for raw_code, raw_count in sorted(payload.items()):
        if not isinstance(raw_code, str) or not isinstance(raw_count, int):
            raise TypeError("Neo4j projection issue summary entries are invalid")
        counts.append(
            ObsidianGraphProjectionIssueCount(
                code=ObsidianGraphProjectionIssueCode(raw_code),
                count=raw_count,
            )
        )
    return tuple(counts)


def _node_parameters(
    node: ObsidianGraphProjectionNode,
    *,
    run_id: str,
) -> Neo4jProjectionNodeParameters:
    return {
        "projection_key": f"{run_id}:note:{node.note_id}",
        "note_id": node.note_id,
        "relative_path": node.relative_path,
        "alexandria_type": node.alexandria_type.value,
        "title": node.title,
        "status": node.status,
        "project": node.project,
    }


def _edge_parameters(
    edge: ObsidianGraphProjectionEdge,
    *,
    run_id: str,
) -> Neo4jProjectionEdgeParameters:
    target_key = (
        f"{run_id}:note:{edge.target_note_id}"
        if edge.target_note_id is not None
        else f"{run_id}:path:{edge.target_path}"
    )
    return {
        "edge_id": edge.edge_id,
        "source_key": f"{run_id}:note:{edge.source_note_id}",
        "source_note_id": edge.source_note_id,
        "source_path": edge.source_path,
        "target_key": target_key,
        "target_note_id": edge.target_note_id,
        "target_path": edge.target_path,
        "relation": edge.relation.value,
        "confidence": edge.confidence,
        "source_kind": edge.source_kind.value,
    }


def _node_from_row(row: Neo4jProjectionRawRow) -> ObsidianGraphProjectionNode:
    return ObsidianGraphProjectionNode(
        note_id=_required_text(row, "note_id"),
        relative_path=_required_text(row, "relative_path"),
        alexandria_type=AlexandriaNoteType(_required_text(row, "alexandria_type")),
        title=_required_text(row, "title"),
        status=_required_text(row, "status"),
        project=_optional_text(row, "project"),
    )


def _edge_from_row(row: Neo4jProjectionRawRow) -> ObsidianGraphProjectionEdge:
    confidence = row.get("confidence")
    if not isinstance(confidence, int | float):
        raise TypeError("Neo4j projection edge confidence must be numeric")
    return ObsidianGraphProjectionEdge(
        edge_id=_required_text(row, "edge_id"),
        source_note_id=_required_text(row, "source_note_id"),
        source_path=_required_text(row, "source_path"),
        target_note_id=_optional_text(row, "target_note_id"),
        target_path=_required_text(row, "target_path"),
        relation=ObsidianRelationType(_required_text(row, "relation")),
        confidence=float(confidence),
        source_kind=ObsidianEdgeSourceKind(_required_text(row, "source_kind")),
    )


def _related_note_from_row(row: Neo4jProjectionRawRow) -> ObsidianGraphRelatedNote:
    score = row.get("score")
    if not isinstance(score, int | float):
        raise TypeError("Neo4j related-note score must be numeric")
    return ObsidianGraphRelatedNote(
        note_id=_required_text(row, "related_note_id"),
        edge_id=_required_text(row, "edge_id"),
        relation=ObsidianRelationType(_required_text(row, "relation")),
        source_kind=ObsidianEdgeSourceKind(_required_text(row, "source_kind")),
        direction=ObsidianGraphDirection(_required_text(row, "direction")),
        score=float(score),
    )


def _context_evidence_from_row(
    row: Neo4jProjectionRawRow,
) -> ObsidianGraphContextEvidence:
    return ObsidianGraphContextEvidence(
        signal=ObsidianGraphContextSignalType(_required_text(row, "signal")),
        edge_id=_required_text(row, "edge_id"),
        source_note_id=_required_text(row, "source_note_id"),
        target_note_id=_required_text(row, "target_note_id"),
        target_title=_required_text(row, "target_title"),
        relation=ObsidianRelationType(_required_text(row, "relation")),
    )


def _required_text(row: Neo4jProjectionRawRow, key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise TypeError(f"Neo4j projection row requires text field {key}")
    return value


def _optional_text(row: Neo4jProjectionRawRow, key: str) -> str | None:
    value = row.get(key)
    if value is None or isinstance(value, str):
        return value
    raise TypeError(f"Neo4j projection row field {key} must be text or null")
