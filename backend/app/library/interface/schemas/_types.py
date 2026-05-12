"""Shared schema helpers."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    """Shared pydantic strict base used by request/response objects."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
    )
