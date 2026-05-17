"""Shared strict Pydantic schema bases."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, ConfigDict, RootModel

RootValueT = TypeVar("RootValueT")


class StrictSchemaModel(BaseModel):
    """Provide the backend-wide default for named-field schemas."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )


class StrictRootSchemaModel(RootModel[RootValueT]):
    """Provide the backend-wide default for root-value schemas."""

    model_config = ConfigDict(
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )
