"""Pydantic contracts for librarian review gateway synthetic payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.shared.types.extra_types import JSONValue


class LibrarianReviewGatewayPayload(BaseModel):
    """Base schema for librarian review gateway payloads."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )


class ReviewMovePlanPayload(LibrarianReviewGatewayPayload):
    """Validated subset of a librarian review move plan."""

    moves: tuple[JSONValue, ...] = Field(default_factory=tuple)

    @field_validator("moves", mode="before")
    @classmethod
    def _list_or_empty(cls, value: object) -> object:
        if isinstance(value, list):
            return value
        return []

    def has_moves(self) -> bool:
        """Return whether the move plan has move candidates.

        Returns:
            True when at least one move candidate exists.
        """
        return bool(self.moves)


class ReviewApplySkippedPayload(LibrarianReviewGatewayPayload):
    """Output schema for non-mutating review apply gateway results."""

    status: Literal["no_op", "confirmation_required"]
    hard_delete_performed: bool = False
    moved: tuple[JSONValue, ...] = Field(default_factory=tuple)
    skipped: tuple[JSONValue, ...] = Field(default_factory=tuple)
    ambiguous: tuple[JSONValue, ...] = Field(default_factory=tuple)
    apply_skipped_reason: Literal["review_move_plan_empty", "confirm_apply_required"]
    move_plan: JSONValue


def review_move_plan_has_moves(payload: JSONValue) -> bool:
    """Return whether a review move plan includes candidates.

    Args:
        payload: Backend move-plan payload.

    Returns:
        True when move candidates are present.
    """
    return ReviewMovePlanPayload.model_validate(_object_or_empty(payload)).has_moves()


def empty_review_apply_payload(move_plan: JSONValue) -> JSONValue:
    """Build a no-op review apply payload through a Pydantic output schema.

    Args:
        move_plan: Dry-run move plan payload.

    Returns:
        JSON-compatible no-op apply payload.
    """
    payload = ReviewApplySkippedPayload(
        status="no_op",
        apply_skipped_reason="review_move_plan_empty",
        move_plan=move_plan,
    )
    return payload.model_dump(mode="json")


def review_apply_confirmation_required_payload(move_plan: JSONValue) -> JSONValue:
    """Build a confirmation-required payload through a Pydantic output schema.

    Args:
        move_plan: Dry-run move plan payload.

    Returns:
        JSON-compatible confirmation-required payload.
    """
    payload = ReviewApplySkippedPayload(
        status="confirmation_required",
        apply_skipped_reason="confirm_apply_required",
        move_plan=move_plan,
    )
    return payload.model_dump(mode="json")


def _object_or_empty(payload: JSONValue) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}
