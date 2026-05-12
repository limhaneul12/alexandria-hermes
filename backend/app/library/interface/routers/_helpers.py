from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from app.library.domain.entities.enums import ItemType
from app.shared.types.extra_types import JSONValue
from fastapi import HTTPException, status


def build_patch_payload(payload: Mapping[str, JSONValue]) -> dict[str, JSONValue]:
    """Build a request payload containing only non-None values.

    Args:
        payload: Raw patch payload.

    Return:
        A new dict without None entries.

    Raises:
        HTTPException: When payload becomes empty.
    """

    updates = {key: value for key, value in payload.items() if value is not None}
    updates_typed = cast(dict[str, JSONValue], updates)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided",
        )
    return updates_typed


def ensure_item_type(
    payload: Mapping[str, JSONValue],
    *,
    expected: ItemType,
    detail: str,
) -> None:
    """Validate item payload belongs to expected type.

    Args:
        payload: Mapped item payload.
        expected: Expected item type.
        detail: HTTP 404 detail message if mismatched.

    Raises:
        HTTPException: If item type does not match.
    """

    if payload.get("item_type") != expected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )
