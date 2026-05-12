"""Pydantic model serialization helper module."""

from __future__ import annotations

from app.shared.serialization.orjson_codec import dumps_json
from app.shared.types.extra_types import JSONObject
from pydantic import BaseModel


def model_to_dict(model: BaseModel) -> JSONObject:
    """Convert a Pydantic model to a JSON-compatible dictionary.

    Args:
        model: See function signature.

    Return:
        Return value.
    """
    return model.model_dump()


def dumps_model(model: BaseModel) -> bytes:
    """Serialize a Pydantic model to orjson bytes.

    Args:
        model: See function signature.

    Return:
        Return value.
    """
    return dumps_json(model_to_dict(model))
