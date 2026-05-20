"""Pydantic model serialization helper tests."""

from __future__ import annotations

from app.shared.schemas.common_schemas import StrictSchemaModel
from app.shared.serialization.model_codec import schema_payload


class ExamplePatchSchema(StrictSchemaModel):
    """Schema used to lock optional serialization behavior."""

    name: str | None = None
    description: str | None = None


def test_schema_payload_omits_unset_fields_when_requested() -> None:
    """schema_payload should preserve explicit nulls while excluding absent fields."""
    schema = ExamplePatchSchema(description=None)

    assert schema_payload(schema, exclude_unset=True) == {"description": None}


def test_schema_payload_omits_none_fields_when_requested() -> None:
    """schema_payload should omit nullable fields when exclude_none is requested."""
    schema = ExamplePatchSchema(name="codex", description=None)

    assert schema_payload(schema, exclude_none=True, exclude_unset=True) == {
        "name": "codex",
    }
