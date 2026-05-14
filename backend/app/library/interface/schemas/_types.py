"""Shared schema helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, RootModel


class StrictSchema(BaseModel):
    """Shared pydantic strict base used by request/response objects."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )


class StrictRootSchema[RootValueT](RootModel[RootValueT]):
    """Shared pydantic root base used by collection response contracts."""

    model_config = ConfigDict(
        frozen=True,
        use_enum_values=True,
        validate_default=True,
    )
