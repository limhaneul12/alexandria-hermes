"""SQL helpers for thin library candidate search."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import cast

from app.library.domain.entities.item_search_hit import ItemSearchCandidate
from app.library.domain.entities.item_search_query import ItemSearchQuery
from app.library.domain.event_enum.item_enums import ItemStatus, ItemType
from app.library.infrastructure.models.category_models import CategoryORM
from app.library.infrastructure.models.item_models import LibraryItemORM
from app.library.infrastructure.repositories.items.fts import (
    build_item_candidate_fts_query,
)
from app.shared.types.extra_types import JSONObject, JSONValue
from sqlalchemy import Select, bindparam, column, exists, func, literal, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.sql.elements import ColumnElement

MAX_CANDIDATE_SEARCH_LIMIT = 100

type CandidateRow = tuple[
    str,
    str,
    str,
    str | None,
    str | None,
    list[str],
    str,
    JSONObject,
    int,
    datetime,
    float,
]
type CandidateStatement = Select[CandidateRow]
type CandidateRowValue = str | int | float | datetime | list[str] | JSONObject | None
type CandidateParameter = str | list[str]


@dataclass(frozen=True, slots=True)
class CandidateSearchPlan:
    """Prepared candidate search SQL and bind parameters."""

    statement: CandidateStatement
    params: dict[str, CandidateParameter]
    has_query: bool


def build_candidate_search_plan(options: ItemSearchQuery) -> CandidateSearchPlan:
    """Build the unpaginated candidate search plan.

    Args:
        options: Normalized candidate search options.

    Returns:
        SQL statement, bind parameters, and query-token status.
    """
    params: dict[str, CandidateParameter] = {}
    has_query = False

    if options.query and options.query.strip():
        fts_query = build_item_candidate_fts_query(
            options.query,
            options.search_fields,
        )
        if fts_query is None:
            return CandidateSearchPlan(_empty_candidate_statement(), params, False)
        params.update(
            {
                key: value
                for key, value in fts_query.parameters.items()
                if isinstance(value, str)
            }
        )
        fts_matches = fts_query.statement.subquery("fts_matches")
        score_column = cast(
            ColumnElement[float],
            (1.0 / (1.0 + func.abs(fts_matches.c.rank))).label("score"),
        )
        statement = _candidate_select(score_column).join(
            fts_matches,
            LibraryItemORM.id == fts_matches.c.item_id,
        )
        has_query = True
    else:
        statement = _candidate_select(literal(0.0).label("score"))

    statement = _apply_scalar_filters(statement, options)
    statement = _apply_json_array_any_filter(
        statement,
        params,
        field=LibraryItemORM.tags,
        values=options.tags_any,
        prefix="tags_any",
    )
    statement = _apply_json_array_all_filter(
        statement,
        params,
        field=LibraryItemORM.tags,
        values=options.tags_all,
        prefix="tags_all",
    )
    statement = _apply_json_array_all_filter(
        statement,
        params,
        field=LibraryItemORM.details,
        detail_path="$.required_tools",
        values=options.required_tools,
        prefix="required_tools",
    )
    return CandidateSearchPlan(statement, params, has_query)


def paginate_candidate_statement(
    statement: CandidateStatement,
    *,
    limit: int,
    offset: int,
) -> CandidateStatement:
    """Apply candidate ordering and pagination.

    Args:
        statement: Unpaginated candidate statement.
        limit: Requested page size.
        offset: Requested row offset.

    Returns:
        Paginated statement.
    """
    bounded_limit = min(MAX_CANDIDATE_SEARCH_LIMIT, max(1, int(limit)))
    bounded_offset = max(0, int(offset))
    paged = (
        statement.order_by(
            column("score").desc(),
            LibraryItemORM.updated_at.desc(),
            LibraryItemORM.id.asc(),
        )
        .limit(bounded_limit)
        .offset(bounded_offset)
    )
    return cast(CandidateStatement, paged)


def candidate_from_mapping(row: RowMapping) -> ItemSearchCandidate:
    """Map one SQLAlchemy row mapping into a search candidate.

    Args:
        row: SQLAlchemy result row mapping.

    Returns:
        Candidate projection without full content.
    """
    return ItemSearchCandidate(
        id=str(_row_value(row, "id")),
        item_type=ItemType(str(_row_value(row, "item_type"))),
        title=str(_row_value(row, "title")),
        summary=_optional_string(_row_value(row, "summary")),
        category_id=_optional_string(_row_value(row, "category_id")),
        tags=_string_list(_row_value(row, "tags")),
        status=ItemStatus(str(_row_value(row, "status"))),
        details=_json_object(_row_value(row, "details")),
        content_char_count=_int_value(_row_value(row, "content_char_count")),
        updated_at=_datetime_value(_row_value(row, "updated_at")),
        score=_float_value(_row_value(row, "score")),
    )


def _apply_scalar_filters(
    statement: CandidateStatement,
    options: ItemSearchQuery,
) -> CandidateStatement:
    if options.item_types:
        statement = statement.where(
            LibraryItemORM.item_type.in_(
                [item_type.value for item_type in options.item_types]
            )
        )
    if options.category_id is not None:
        if options.include_descendant_categories:
            category_tree = (
                select(CategoryORM.id)
                .where(CategoryORM.id == options.category_id)
                .cte(name="category_tree", recursive=True)
            )
            category_tree = category_tree.union_all(
                select(CategoryORM.id).where(
                    CategoryORM.parent_id == category_tree.c.id
                )
            )
            statement = statement.where(
                LibraryItemORM.category_id.in_(select(category_tree.c.id))
            )
        else:
            statement = statement.where(
                LibraryItemORM.category_id == options.category_id
            )
    if options.status is not None:
        statement = statement.where(LibraryItemORM.status == options.status.value)
    if options.source_type is not None:
        statement = statement.where(
            LibraryItemORM.source_type == options.source_type.value
        )
    if options.created_by_type is not None:
        statement = statement.where(
            LibraryItemORM.created_by_type == options.created_by_type.value
        )
    if options.created_by_name is not None:
        statement = statement.where(
            LibraryItemORM.created_by_name == options.created_by_name
        )
    if options.updated_since is not None:
        statement = statement.where(LibraryItemORM.updated_at >= options.updated_since)
    if options.updated_before is not None:
        statement = statement.where(LibraryItemORM.updated_at <= options.updated_before)
    if options.prompt_kind is not None:
        statement = statement.where(
            func.json_extract(LibraryItemORM.details, "$.prompt_kind")
            == options.prompt_kind.value
        )
    if options.risk_level is not None:
        statement = statement.where(
            func.json_extract(LibraryItemORM.details, "$.risk_level")
            == options.risk_level.value
        )
    return statement


def _candidate_select(score_column: ColumnElement[float]) -> CandidateStatement:
    statement = select(
        LibraryItemORM.id.label("id"),
        LibraryItemORM.item_type.label("item_type"),
        LibraryItemORM.title.label("title"),
        LibraryItemORM.summary.label("summary"),
        LibraryItemORM.category_id.label("category_id"),
        LibraryItemORM.tags.label("tags"),
        LibraryItemORM.status.label("status"),
        LibraryItemORM.details.label("details"),
        func.length(LibraryItemORM.content).label("content_char_count"),
        LibraryItemORM.updated_at.label("updated_at"),
        score_column,
    )
    return cast(CandidateStatement, statement)


def _empty_candidate_statement() -> CandidateStatement:
    return _candidate_select(literal(0.0).label("score")).where(
        literal(1) == literal(0)
    )


def _apply_json_array_any_filter(
    statement: CandidateStatement,
    params: dict[str, CandidateParameter],
    *,
    field,
    detail_path: str | None = None,
    values: tuple[str, ...],
    prefix: str,
) -> CandidateStatement:
    if not values:
        return statement
    key = f"{prefix}_values"
    params[key] = list(values)
    json_values = _json_each(field, detail_path=detail_path)
    return statement.where(
        exists(
            select(literal(1))
            .select_from(json_values)
            .where(json_values.c.value.in_(bindparam(key, expanding=True)))
        )
    )


def _apply_json_array_all_filter(
    statement: CandidateStatement,
    params: dict[str, CandidateParameter],
    *,
    field,
    detail_path: str | None = None,
    values: tuple[str, ...],
    prefix: str,
) -> CandidateStatement:
    for index, value in enumerate(values):
        key = f"{prefix}_{index}"
        params[key] = value
        json_values = _json_each(field, detail_path=detail_path)
        statement = statement.where(
            exists(
                select(literal(1))
                .select_from(json_values)
                .where(json_values.c.value == bindparam(key))
            )
        )
    return statement


def _json_each(field, *, detail_path: str | None):
    if detail_path is None:
        return func.json_each(field).table_valued("value")
    return func.json_each(field, detail_path).table_valued("value")


def _row_value(row: RowMapping, key: str) -> CandidateRowValue:
    return cast(CandidateRowValue, row[key])


def _optional_string(value: CandidateRowValue) -> str | None:
    if value is None:
        return None
    return str(value)


def _string_list(value: CandidateRowValue) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _json_object(value: CandidateRowValue) -> JSONObject:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): item
        for key, item in value.items()
        if isinstance(key, str) and _is_json_value(item)
    }


def _datetime_value(value: CandidateRowValue) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    message = "candidate updated_at must be a datetime"
    raise TypeError(message)


def _int_value(value: CandidateRowValue) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float | str):
        return int(value)
    return 0


def _float_value(value: CandidateRowValue) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        return float(value)
    return 0.0


def _is_json_value(value: JSONValue) -> bool:
    if value is None or isinstance(value, str | int | float | bool):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item) for key, item in value.items()
        )
    return False
